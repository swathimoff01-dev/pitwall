import re
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

BASE = "https://www.fia.com"
F1_DOCS = "/documents/championships/fia-formula-one-world-championship-14"
START_PAGE = F1_DOCS + "/season/season-2025-2071"  # a known season page; it links to the others
USER_AGENT = "pitwall-portfolio/0.1 (personal, non-commercial learning project)"
MIN_GAP_S = 3.0  # one request every 3 seconds

SEASON_RE = re.compile(r"/season/season-(\d{4})-(\d+)")
DOC_RE = re.compile(
    r"(?:Doc\s+(\d+)\s+-\s+)?(.+?)\s+Published on\s+(\d{2})\.(\d{2})\.(\d{2})\s+(\d{2}:\d{2})"
)


@dataclass
class DocLink:
    season: int
    event: str
    doc_no: int | None
    title: str      # "Decision - Car 16 - Alleged Causing a Collision"
    category: str   # first part of the title: "Decision", "Infringement", "Summons", ...
    published: str  # "2025-08-31 20:14" (CET, as the FIA shows it)
    url: str

def safe_url(url: str) -> str:
    """Re-encode the path so raw spaces or '%' in FIA file names become a valid URL."""
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=quote(unquote(parts.path), safe="/")))


def parse_doc_links(html: str, season: int, event: str) -> list[DocLink]:
    """Every linked document on an event page. Recalled documents have no link, so they are skipped."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.select('a[href*="/decision-document/"]'):
        m = DOC_RE.search(a.get_text(" ", strip=True))
        if not m:
            continue
        doc_no, title, d, mo, y, hm = m.groups()
        links.append(DocLink(season, event, int(doc_no) if doc_no else None, title.strip(),
                             title.split(" - ")[0].strip(),
                              f"20{y}-{mo}-{d} {hm}", safe_url(urljoin(BASE, a["href"]))))
    return links


def parse_season_paths(html: str) -> dict[int, str]:
    """Season page paths, found anywhere in the HTML (links or dropdown values)."""
    return {int(y): f"{F1_DOCS}/season/season-{y}-{sid}" for y, sid in SEASON_RE.findall(html)}


class FiaClient:
    def __init__(self):
        self._http = httpx.Client(timeout=60, follow_redirects=True,
                                  headers={"User-Agent": USER_AGENT})
        robots = self._http.get(urljoin(BASE, "/robots.txt"))
        self._robots = RobotFileParser()
        self._robots.parse(robots.text.splitlines() if robots.status_code == 200 else [])
        self._last = 0.0
        self.requests = 1

    def _get(self, url: str) -> httpx.Response:
        if not self._robots.can_fetch(USER_AGENT, url):
            raise PermissionError(f"robots.txt does not allow {url}")
        for attempt in range(5):
            gap = MIN_GAP_S - (time.monotonic() - self._last)
            if gap > 0:
                time.sleep(gap)
            self._last = time.monotonic()
            self.requests += 1
            try:
                resp = self._http.get(url)
            except httpx.TransportError:
                resp = None
            if resp is not None and resp.status_code == 200:
                return resp
            if resp is not None and resp.status_code not in (429, 500, 502, 503, 504):
                resp.raise_for_status()
            wait = min(15 * 2**attempt, 300)
            print(f"⚠️  {url}: retry {attempt + 1}/5 in {wait}s")
            time.sleep(wait)
        raise RuntimeError(f"Giving up on {url}")

    def get_text(self, path_or_url: str) -> str:
        return self._get(urljoin(BASE, path_or_url)).text

    def download(self, url: str, dest: Path) -> bool:
        """Save url to dest unless it is already there. Returns True if it downloaded."""
        if dest.exists() and dest.stat().st_size > 0:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".part")  # never leave a half-written PDF behind
        content = self._get(url).content
        if not content.startswith(b"%PDF"):
            raise ValueError("got a web page instead of a PDF (probably a bot check)")
        tmp.write_bytes(content)
        tmp.replace(dest)
        return True