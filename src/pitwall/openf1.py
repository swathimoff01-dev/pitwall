"""A polite OpenF1 client: free public API, limit of 30 requests per minute."""

import hashlib
import json
import time
from datetime import date
from pathlib import Path

import httpx

BASE_URL = "https://api.openf1.org/v1"
MIN_GAP_S = 2.5  # 24 requests per minute, under the 30 per minute limit
CACHE_DIR = Path("data/cache/openf1")


class OpenF1Client:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self._http = httpx.Client(timeout=90, headers={"User-Agent": "pitwall-portfolio/0.1"})
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._last = 0.0
        self.network_calls = 0

    def _fetch(self, endpoint: str, params: dict) -> list:
        for attempt in range(6):
            gap = MIN_GAP_S - (time.monotonic() - self._last)
            if gap > 0:
                time.sleep(gap)
            self._last = time.monotonic()
            self.network_calls += 1
            try:
                resp = self._http.get(f"{BASE_URL}/{endpoint}", params=params)
            except httpx.TransportError:
                resp = None
            if resp is not None and resp.status_code == 200:
                return resp.json()
            if resp is not None and resp.status_code == 404:
                return []  # OpenF1 answers 404 when there are no matching rows
            if resp is not None and resp.status_code not in (429, 500, 502, 503, 504):
                resp.raise_for_status()  # a real error; retrying won't help
            wait = min(10 * 2**attempt, 120)
            print(f"⚠️  {endpoint} {params}: retry {attempt + 1}/6 in {wait}s")
            time.sleep(wait)
        raise RuntimeError(f"Giving up on {endpoint} {params}")

    def get(self, endpoint: str, season: int, **params) -> list:
        """season only decides caching: finished years never change, so they are cached."""
        finished = season < date.today().year
        key = hashlib.sha256(json.dumps([endpoint, params], sort_keys=True).encode()).hexdigest()[:24]
        file = self._cache_dir / f"{key}.json"
        if finished and file.exists():
            return json.loads(file.read_text(encoding="utf-8"))
        rows = self._fetch(endpoint, params)
        if finished:
            file.write_text(json.dumps(rows), encoding="utf-8")
        return rows