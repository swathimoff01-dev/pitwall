"""Load FIA Sporting Regulations PDFs into regulation_articles. Safe to rerun."""

from pathlib import Path

import psycopg

from pitwall.config import get_settings
from pitwall.regs_parser import file_metadata, parse_pdf

RAW_DIR = Path("data/raw/regulations")
LONG_CHARS = 2000  # roughly the most our embedding model reads at once (~512 tokens)


def main() -> None:
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(f"No PDFs found in {RAW_DIR}")
    s = get_settings()
    with psycopg.connect(s.admin_conninfo(), options="-c search_path=pitwall,public") as conn:
        for pdf in pdfs:
            season, issue, published = file_metadata(pdf)
            chunks = parse_pdf(pdf)
            with conn.transaction():  # replace this season's rulebook as one unit
                conn.execute("DELETE FROM regulation_articles WHERE season = %s", (season,))
                for c in chunks:
                    conn.execute(
                        """INSERT INTO regulation_articles
                           (season, issue, published_on, source_file, doc_version,
                            article_no, title, body)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (season, issue, published, pdf.name,
                         f"{season} F1 Sporting Regulations, Issue {issue}",
                         c.article_no, c.title, c.body),
                    )
            longest = max(chunks, key=lambda c: len(c.body))
            n_long = sum(len(c.body) > LONG_CHARS for c in chunks)
            print(f"✅ {season} issue {issue}: {len(chunks)} sub-articles in "
                  f"{len({c.article for c in chunks})} articles; longest is {longest.article_no} "
                  f"({len(longest.body)} chars); {n_long} over {LONG_CHARS} chars")


if __name__ == "__main__":
    main()