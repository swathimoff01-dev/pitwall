"""Parse the downloaded decision PDFs (listed in manifest.jsonl) into stewards_decisions.
Safe to rerun; run it again whenever more PDFs have been downloaded."""

import json
from collections import Counter
from pathlib import Path

import psycopg

from pitwall.config import get_settings
from pitwall.decision_parser import Decision, match_driver_name, parse_decision_pdf

MANIFEST = Path("data/raw/decisions/manifest.jsonl")


def main() -> None:
    rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines()]
    s = get_settings()
    with psycopg.connect(s.admin_conninfo(), options="-c search_path=pitwall,public") as conn:
        race_ids = {(season, name): rid for season, name, rid in
                    conn.execute("SELECT season, name, race_id FROM races").fetchall()}
        status, types, unmatched = Counter(), Counter(), 0
        with conn.transaction():
            for r in rows:
                try:
                    d = parse_decision_pdf(Path(r["file"]))
                except Exception as exc:  # a broken PDF is recorded, not fatal
                    print(f"❌ {r['file']}: {exc}")
                    d = Decision()
                race_id = race_ids.get((r["season"], r["event"]))
                driver_id = None
                if d.driver and race_id:
                    candidates = conn.execute(
                        "SELECT d.driver_id, d.family_name FROM results x "
                        "JOIN drivers d USING (driver_id) WHERE x.race_id = %s", (race_id,)
                    ).fetchall()
                    driver_id = match_driver_name(candidates, d.driver)
                    unmatched += driver_id is None
                conn.execute("DELETE FROM stewards_decisions WHERE source_file = %s", (r["file"],))
                conn.execute(
                    """INSERT INTO stewards_decisions
                       (season, race_id, doc_ref, source_file, title, category, doc_no, doc_date,
                        car_no, driver_id, competitor, session, incident_summary, infringement,
                        articles_cited, penalty, penalty_type, time_penalty_s, penalty_points,
                        reasoning, parse_status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                               %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (r["season"], race_id, r["url"], r["file"], r["title"], r["category"],
                     d.doc_no, d.doc_date, d.car_no, driver_id, d.competitor, d.session,
                     d.fact or r["title"], d.infringement, d.articles, d.decision,
                     d.penalty_type, d.time_penalty_s, d.penalty_points, d.reason, d.parse_status),
                )
                status[d.parse_status] += 1
                types[d.penalty_type or "none"] += 1
    print(f"✅ {len(rows)} decisions loaded. Parse status: {dict(status)}")
    print(f"   Penalty types: {dict(types.most_common())}")
    print(f"   Driver named but not matched to our drivers table: {unmatched}")


if __name__ == "__main__":
    main()