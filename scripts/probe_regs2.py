"""Spike 2: show the text around the penalties article to see how article headings look."""

import sys

import pymupdf

doc = pymupdf.open(sys.argv[1])
lines = [ln.strip() for page in doc for ln in page.get_text().splitlines() if ln.strip()]
hits = [i for i, ln in enumerate(lines) if ln == "54.1"]
print(f"page count: {doc.page_count}, bookmarks: {len(doc.get_toc())}, '54.1' found {len(hits)} times")
i = hits[-1]
print("\n".join(lines[i - 12 : i + 20]))