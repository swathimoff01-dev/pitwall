"""Spike: print the raw text of a few decision PDFs to see how their fields are laid out."""

import json
from pathlib import Path

import pymupdf

manifest = Path("data/raw/decisions/manifest.jsonl")
rows = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines()]
picks = ([r for r in rows if r["category"] == "Infringement"][:2]
         + [r for r in rows if r["category"] == "Decision"][:1])

for r in picks:
    doc = pymupdf.open(r["file"])
    text = "\n".join(page.get_text() for page in doc)
    print(f"\n===== {r['title']} ({doc.page_count} pages) =====")
    print(text[:2500])