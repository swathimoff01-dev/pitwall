"""Extract labelled fields from FIA stewards' decision PDFs."""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

import pymupdf

# ---- labels on the decision form ----
# The FIA uses three spellings for this label, and glues it to its value on the same line
INFRINGEMENT_RE = re.compile(r"^(?:Infringement|Infringment|Offence)\s*(.*)$")
LABELS = {"No / Driver": "driver", "Competitor": "competitor", "Time": "incident_time",
          "Session": "session", "Fact": "fact", "Decision": "decision", "Reason": "reason"}
END_MARKER = "Competitors are reminded"  # fixed sentence after the reason

# ---- values inside fields ----
DRIVER_RE = re.compile(r"^(\d+)\s*[-–—‑]\s*(.+)$")  # "63 - George Russell", any kind of dash
POINTS_RE = re.compile(r"(\d+)\s+penalty points?", re.I)
SECONDS_RE = re.compile(r"(\d+)\s*second", re.I)

# ---- rule citations ----
DOC_NAME_RE = re.compile(
    r"Sporting Regulations?|Technical Regulations?|International Sporting Code", re.I)
_ITEM = r"(?:\.?[a-z]\b|\s?\(?[a-z]{1,4}\))"   # "2b", "12.2.1.l", " c)", "(c)", " i)"
_NUM = rf"\d+(?:\.\d+)*{_ITEM}?"
ART_LIST_RE = re.compile(rf"\bArt(?:icle)?s?\.?\s*({_NUM}(?:\s*(?:,|and|&)\s*{_NUM})*)", re.I)
NUM_RE = re.compile(r"(\d+(?:\.\d+)*)(?:\.?([a-z])\b|\s?\(?([a-z]{1,4})\))?", re.I)
CHAPTER_RE = re.compile(r"Chapter\s+([IVX]+)\b")

# ---- penalty types, checked in order; the first match wins ----
PENALTY_TYPES = [
    ("no_further_action", re.compile(r"no further action", re.I)),
    ("disqualification", re.compile(r"disqualif", re.I)),
    ("drive_through", re.compile(r"drive[- ]through", re.I)),
    ("stop_go", re.compile(r"stop[ /&]*(?:and )?go", re.I)),
    ("grid_penalty", re.compile(r"\bgrid\b", re.I)),
    ("time_penalty", re.compile(r"second", re.I)),
    ("reprimand", re.compile(r"reprimand", re.I)),
    ("fine", re.compile(r"\bfine|€", re.I)),
    ("lap_time_deleted", re.compile(r"lap time", re.I)),
]


@dataclass
class Decision:
    doc_no: int | None = None
    doc_date: date | None = None
    car_no: int | None = None
    driver: str | None = None
    competitor: str | None = None
    session: str | None = None
    fact: str | None = None
    infringement: str | None = None
    decision: str | None = None
    reason: str | None = None
    articles: list[str] = field(default_factory=list)
    penalty_type: str | None = None
    time_penalty_s: int | None = None
    penalty_points: int | None = None

    @property
    def parse_status(self) -> str:
        if self.fact and self.decision:
            return "full"
        return "partial" if self.decision else "unparsed"


def classify_penalty(text: str) -> tuple[str, int | None]:
    for name, pattern in PENALTY_TYPES:
        if pattern.search(text):
            seconds = SECONDS_RE.search(text) if name == "time_penalty" else None
            return name, int(seconds.group(1)) if seconds else None
    return "other", None


def extract_articles(text: str) -> list[str]:
    """Normalised citations such as 'SR 54.4 c)', 'ISC App L Ch IV Art 2 b)', 'TR 6.5.2'.
    The text is split at each rulebook name; every article belongs to the rulebook
    named right after it."""
    found, start = [], 0
    for doc in DOC_NAME_RE.finditer(text):
        segment, start = text[start:doc.end()], doc.end()
        name = doc.group().lower()
        if "technical" in name:
            prefix = "TR"
        elif "sporting regulation" in name:
            prefix = "SR"
        elif "appendix l" in segment.lower():
            chapter = CHAPTER_RE.search(segment)
            prefix = f"ISC App L Ch {chapter.group(1) if chapter else '?'} Art"
        else:
            prefix = "ISC"
        for art_list in ART_LIST_RE.finditer(segment):
            for m in NUM_RE.finditer(art_list.group(1)):
                item = (m.group(2) or m.group(3) or "").lower()
                found.append(f"{prefix} {m.group(1)}" + (f" {item})" if item else ""))
    return list(dict.fromkeys(found))  # remove duplicates, keep order


def _header(lines: list[str], label: str) -> str | None:
    """Value on the line after the first exact `label` line."""
    for i, ln in enumerate(lines[:-1]):
        if ln == label:
            return lines[i + 1]
    return None


def parse_decision_text(text: str) -> Decision:
    # PDFs often use non-breaking spaces; split() treats every kind of space alike
    lines = [" ".join(ln.split()) for ln in text.splitlines() if ln.strip()]
    d = Decision()

    doc_no = _header(lines, "Document")
    d.doc_no = int(doc_no) if doc_no and doc_no.isdigit() else None
    try:
        d.doc_date = datetime.strptime(_header(lines, "Date") or "", "%d %B %Y").date()
    except ValueError:
        pass

    # Fields start at the first driver/competitor label, so the header's "Time" is never confused
    start = next((i for i, ln in enumerate(lines) if ln in ("No / Driver", "Competitor")), None)
    if start is None:
        return d
    parts: dict[str, list[str]] = {}
    current = None
    for ln in lines[start:]:
        if ln.startswith(END_MARKER):
            break
        if current != "reason":  # inside the reason, words like "Decision" are just text
            if ln in LABELS:
                current = LABELS[ln]
                parts[current] = []
                continue
            if m := INFRINGEMENT_RE.match(ln):
                current = "infringement"
                parts[current] = [m.group(1)] if m.group(1) else []
                continue
        if current:
            parts[current].append(ln)
    value = {k: " ".join(v).strip() or None for k, v in parts.items()}

    if value.get("driver") and (m := DRIVER_RE.match(value["driver"])):
        d.car_no, d.driver = int(m.group(1)), m.group(2).strip()
    d.competitor, d.session = value.get("competitor"), value.get("session")
    d.fact, d.decision, d.reason = value.get("fact"), value.get("decision"), value.get("reason")
    d.infringement = value.get("infringement")

    if d.infringement:
        d.articles = extract_articles(d.infringement)
    if d.decision:
        d.penalty_type, d.time_penalty_s = classify_penalty(d.decision)
        if m := POINTS_RE.search(d.decision):
            d.penalty_points = int(m.group(1))
    return d


def parse_decision_pdf(path) -> Decision:
    with pymupdf.open(path) as doc:
        return parse_decision_text("\n".join(page.get_text() for page in doc))


def fold(s: str) -> str:
    """Lower-case and strip accents, so 'Pérez' matches 'Perez'."""
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c)).casefold()


def match_driver_name(candidates: list[tuple[str, str]], name: str) -> str | None:
    """candidates: (driver_id, family_name) of drivers in this race. Matches whole words, so
    'Nyck de Vries' -> 'de Vries' and 'Zhou Guanyu' -> 'Zhou'."""
    padded = f" {fold(name)} "
    hits = {did for did, family in candidates if family and f" {fold(family)} " in padded}
    return hits.pop() if len(hits) == 1 else None