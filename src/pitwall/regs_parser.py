"""Parse FIA Formula 1 Sporting Regulations PDFs (2023-2025 format) into one chunk per sub-article."""

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pymupdf

ARTICLE_RE = re.compile(r"^(\d{1,3})\)$")          # "54)" on its own line
SUB_RE = re.compile(r"^(\d{1,3})\.(\d{1,2})$")     # "54.2" on its own line
MARKER_RE = re.compile(r"^(?:[a-z]|[ivx]+)\)$")    # "a)", "iv)" on their own line
PAGE_NO_RE = re.compile(r"^\d+/\d+$")              # "63/119"
FILENAME_RE = re.compile(
    r"fia_(\d{4})_formula_1_sporting_regulations_-_issue_(\d+)_-_(\d{4})-(\d{2})-(\d{2})"
)
BOILERPLATE_SHARE = 0.8  # a line on 80%+ of pages is a header or footer


@dataclass
class Chunk:
    article: int
    sub: int
    title: str  # parent article title, e.g. "INCIDENTS DURING THE SPRINT SESSION OR THE RACE"
    body: str

    @property
    def article_no(self) -> str:
        return f"{self.article}.{self.sub}"


def file_metadata(path: Path) -> tuple[int, int, date]:
    """Season, issue and publish date, read from the FIA filename."""
    m = FILENAME_RE.search(path.name.lower())
    if not m:
        raise ValueError(f"Unexpected filename (keep the FIA name): {path.name}")
    season, issue, y, mo, d = (int(g) for g in m.groups())
    return season, issue, date(y, mo, d)


def clean_pages(pages: list[list[str]]) -> list[str]:
    """Drop headers/footers (lines found on most pages) and page numbers; flatten to one list."""
    on_pages = Counter(line for page in pages for line in set(page))
    boilerplate = {
        line for line, n in on_pages.items()
        if n >= BOILERPLATE_SHARE * len(pages) and not MARKER_RE.match(line)
    }
    return [ln for page in pages for ln in page
            if ln not in boilerplate and not PAGE_NO_RE.match(ln)]


def tidy(body_lines: list[str]) -> str:
    """Join wrapped PDF lines; start each a) / i) item on its own line."""
    parts = [f"\n{ln}" if MARKER_RE.match(ln) else ln for ln in body_lines]
    text = re.sub(r"\s*\n\s*", "\n", " ".join(parts))
    return re.sub(r"[ \t]+", " ", text).strip()


def chunk_lines(lines: list[str]) -> list[Chunk]:
    titles: dict[int, str] = {}
    bodies: dict[tuple[int, int], list[str]] = {}
    article: int | None = None
    current: tuple[int, int] | None = None
    in_title = False
    for i, ln in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        # A main article is "54)" followed by an ALL-CAPS title line
        if (m := ARTICLE_RE.match(ln)) and nxt.isupper():
            article, current, in_title = int(m.group(1)), None, True
            titles[article] = ""
            continue
        if in_title and ln.isupper():
            titles[article] = f"{titles[article]} {ln}".strip()  # titles can wrap
            continue
        in_title = False
        if ln.isupper() and ln.startswith("APPENDIX"):  # stop before appendices
            article, current = None, None
            continue
        m = SUB_RE.match(ln)
        if m and article is not None and int(m.group(1)) == article:
            current = (article, int(m.group(2)))
            bodies[current] = []  # a later occurrence replaces the table of contents
            continue
        if current is not None:
            bodies[current].append(ln)
    return [Chunk(a, s, titles.get(a, ""), tidy(body))
            for (a, s), body in sorted(bodies.items()) if body]


def parse_pdf(path: Path) -> list[Chunk]:
    doc = pymupdf.open(path)
    pages = [[ln.strip() for ln in page.get_text().splitlines() if ln.strip()] for page in doc]
    return chunk_lines(clean_pages(pages))