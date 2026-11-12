"""Find and download FIA stewards' decision PDFs for the seasons in our races table."""

import argparse
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from urllib.parse import quote, unquote

import psycopg

from pitwall.config import get_settings
from pitwall.fia_docs import START_PAGE, FiaClient, parse_doc_links, parse_season_paths

OUT_DIR = Path("data/raw/decisions")
EVENT_ALIASES = {(2023, "São Paulo Grand Prix"): "SÃO PAULO GRAND PRIX"}

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", type=int, nargs="+", default=[2023, 2024, 2025])
    ap.add_argument("--keep", nargs="+", default=["Decision", "Infringement"],
                    help="document categories to download")
    ap.add_argument("--dry-run", action="store_true",
                    help="only list what exists; download nothing")
    args = ap.parse_args()

    s = get_settings()
    with psycopg.connect(s.admin_conninfo(), options="-c search_path=pitwall,public") as conn:
        races = conn.execute(
            "SELECT season, name FROM races WHERE season = ANY(%s) AND race_date <= current_date "
            "ORDER BY season, round", (args.seasons,)
        ).fetchall()

    client = FiaClient()
    season_paths = parse_season_paths(client.get_text(START_PAGE))
    print("Season pages found:", {y: p.rsplit("/", 1)[-1] for y, p in sorted(season_paths.items())})

    kept = []
    for season in args.seasons:
        path = season_paths.get(season)
        if path is None:
            print(f"❌ {season}: no season page found on the FIA site; skipped")
            continue
        categories = Counter()
        for _, name in (r for r in races if r[0] == season):
            fia_name = EVENT_ALIASES.get((season, name), name)
            links = parse_doc_links(client.get_text(f"{path}/event/{quote(fia_name)}"), season, name)
            if not links:
                print(f"⚠️  {season} {name}: no documents found (name may differ on the FIA site)")
            categories.update(link.category for link in links)
            kept += [link for link in links if link.category in args.keep]
        print(f"\n{season} document categories (top 15):")
        for cat, n in categories.most_common(15):
            print(f"   {n:4}  {cat}")

    print(f"\nTo download: {len(kept)} documents in categories {args.keep} "
          f"(about {len(kept) * 3 // 60} minutes)")
    if args.dry_run:
        return

    manifest = OUT_DIR / "manifest.jsonl"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    new, failures = 0, []
    with manifest.open("w", encoding="utf-8") as f:
        for i, link in enumerate(kept, 1):
            dest = OUT_DIR / str(link.season) / unquote(link.url.rsplit("/", 1)[-1])
            try:
                new += client.download(link.url, dest)
            except Exception as exc:  # one bad document must not stop the whole batch
                failures.append({**asdict(link), "error": str(exc)})
                print(f"❌ {link.season} {link.event}: {link.title} ({exc})")
                continue
            f.write(json.dumps({**asdict(link), "file": dest.as_posix()}) + "\n")
            if i % 50 == 0:
                print(f"   {i}/{len(kept)} done ({new} new)")
    if failures:
        (OUT_DIR / "failures.jsonl").write_text(
            "".join(json.dumps(x) + "\n" for x in failures), encoding="utf-8")
    print(f"✅ {len(kept) - len(failures)} documents in {manifest} "
          f"({new} newly downloaded); {len(failures)} failed")


if __name__ == "__main__":
    main()