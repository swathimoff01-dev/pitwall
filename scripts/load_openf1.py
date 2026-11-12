"""Load laps, stints and race control messages from OpenF1. Safe to rerun at any time."""

import argparse

import psycopg

from pitwall.config import get_settings
from pitwall.ingest_openf1 import load_season
from pitwall.openf1 import OpenF1Client

FIRST_OPENF1_SEASON = 2023  # the free archive starts here


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-season", type=int, default=FIRST_OPENF1_SEASON)
    ap.add_argument("--to-season", type=int, default=None,
                    help="default: the latest season already in our races table")
    args = ap.parse_args()

    client = OpenF1Client()
    s = get_settings()
    with psycopg.connect(s.admin_conninfo(), options="-c search_path=pitwall,public") as conn:
        last = args.to_season or conn.execute("SELECT max(season) FROM races").fetchone()[0]
        for season in range(args.from_season, last + 1):
            with conn.transaction():  # one season = all or nothing
                races, laps, stints, msgs = load_season(client, conn.cursor(), season)
            print(f"✅ {season}: {races} races, {laps} laps, {stints} stints, {msgs} race control "
                  f"messages (network calls so far: {client.network_calls})")


if __name__ == "__main__":
    main()