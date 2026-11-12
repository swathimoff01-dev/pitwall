"""Spike: see how a regulations PDF is laid out before writing the parser."""

import re
import sys
from collections import Counter

import pymupdf

doc = pymupdf.open(sys.argv[1])
print(f"{doc.page_count} pages; built-in bookmarks: {len(doc.get_toc())}")
for level, title, page in doc.get_toc()[:15]:
    print("  " * level, title, "-> page", page)

# Headings are usually bigger or bold, so see which font styles exist
styles = Counter()
for page in doc:
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                if span["text"].strip():
                    weight = "bold" if span["flags"] & 16 else "normal"
                    styles[(round(span["size"], 1), weight)] += len(span["text"])
print("\nText by font size and weight (characters):", styles.most_common(8))

# Lines that look like article numbers
pattern = re.compile(r"^(ARTICLE\s+\S+|[A-Z]?\d+(\.\d+)+)\b")
hits = [ln.strip() for p in doc for ln in p.get_text().splitlines() if pattern.match(ln.strip())]
print(f"\nLines that look like article numbers: {len(hits)}")
for h in hits[:25]:
    print("   ", h[:90])

# Lines repeated across many pages = headers and footers to strip
repeats = Counter(ln.strip() for p in doc for ln in p.get_text().splitlines() if ln.strip())
print("\nMost repeated lines (likely headers/footers):")
for ln, n in repeats.most_common(8):
    print(f"   {n}x  {ln[:80]}")

print("\n--- raw text of page 20 ---")
print(doc[min(19, doc.page_count - 1)].get_text()[:1500])