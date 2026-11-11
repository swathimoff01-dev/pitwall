"""A polite Jolpica-F1 client: rate-limited, retrying, cached, paginated."""

import hashlib
import json
import time
from collections import deque
from datetime import date
from pathlib import Path

import httpx

BASE_URL = "https://api.jolpi.ca/ergast/f1"
PAGE_SIZE = 100  # the API's maximum rows per call
MIN_GAP_S = 0.3  # ~3 requests/second, under the 4/second burst limit
HOURLY_CAP = 450  # under the 500/hour sustained limit, leaving headroom
CACHE_DIR = Path("data/cache/jolpica")


class JolpicaClient:
    def __init__(self, cache_dir: Path = CACHE_DIR, refresh_seasons: set[int] | None = None):
        self._http = httpx.Client(timeout=30, headers={"User-Agent": "pitwall-portfolio/0.1"})
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._refresh = refresh_seasons or set()
        self._sent: deque[float] = deque()  # when our recent requests went out
        self._last = 0.0
        self.network_calls = 0

    # ---- rate limiting -------------------------------------------------
    def _wait_for_slot(self) -> None:
        now = time.monotonic()
        while self._sent and now - self._sent[0] > 3600:  # forget calls older than 1 hour
            self._sent.popleft()
        if len(self._sent) >= HOURLY_CAP:
            pause = 3600 - (now - self._sent[0]) + 1
            print(f"⏳ Hourly budget used. Sleeping {pause / 60:.0f} min (Ctrl+C is safe; rerun resumes).")
            time.sleep(pause)
        gap = MIN_GAP_S - (time.monotonic() - self._last)
        if gap > 0:
            time.sleep(gap)

    # ---- one network call, with retry + exponential backoff ------------
    def _fetch(self, path: str, params: dict) -> dict:
        for attempt in range(6):
            self._wait_for_slot()
            self._last = time.monotonic()
            self._sent.append(self._last)
            self.network_calls += 1
            try:
                resp = self._http.get(f"{BASE_URL}/{path}", params=params)
            except httpx.TransportError:
                resp = None
            if resp is not None and resp.status_code == 200:
                return resp.json()
            if resp is not None and resp.status_code not in (429, 500, 502, 503, 504):
                resp.raise_for_status()  # a real error (e.g. 404); retrying won't help
            wait = min(5 * 2**attempt, 120)
            if resp is not None and resp.headers.get("Retry-After", "").isdigit():
                wait = max(wait, int(resp.headers["Retry-After"]))
            print(f"⚠️  {path}: retry {attempt + 1}/6 in {wait}s")
            time.sleep(wait)
        raise RuntimeError(f"Giving up on {path}")

    # ---- cache layer ----------------------------------------------------
    def get(self, path: str, season: int | None = None, offset: int = 0) -> dict:
        finished = season is not None and season < date.today().year  # can't change anymore
        file = self._cache_dir / (hashlib.sha256(f"{path}|{offset}".encode()).hexdigest()[:24] + ".json")
        if finished and season not in self._refresh and file.exists():
            return json.loads(file.read_text(encoding="utf-8"))
        data = self._fetch(path, {"limit": PAGE_SIZE, "offset": offset})
        if finished:
            file.write_text(json.dumps(data), encoding="utf-8")
        return data

    # ---- pagination -----------------------------------------------------
    def pages(self, path: str, season: int):
        """Yield each page's MRData until every row has been seen."""
        offset = 0
        while True:
            mr = self.get(path, season, offset)["MRData"]
            yield mr
            offset += int(mr["limit"])  # the server may use a smaller limit than we asked for
            if offset >= int(mr["total"]):
                break