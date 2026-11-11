"""Load seasons of Jolpica data into Postgres. Safe to rerun at any time."""

import argparse
from datetime import date

import psycopg

from pitwall.config import get_settings
from pitwall.ingest_jolpica import load_pit_stops, load_results, load_schedule
from pitwall.jolpica import JolpicaClient

PIT_STOPS_FROM = 2012  # the source has no pit stop data before this


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-season", type=int, default=1999)
    ap.add_argument("--to-season", type=int, default=date.today().year)
    ap.add_argument("--refresh", type=int, nargs="*", default=[],
                    help="seasons to re-download even if cached")
    args = ap.parse_args()

    client = JolpicaClient(refresh_seasons=set(args.refresh))
    s = get_settings()
    with psycopg.connect(s.admin_conninfo(), options="-c search_path=pitwall,public") as conn:
        for season in range(args.from_season, args.to_season + 1):
            with conn.transaction():  # one season = all or nothing
                cur = conn.cursor()
                races = load_schedule(client, cur, season)
                results = load_results(client, cur, season)
                stops = (load_pit_stops(client, cur, season, date.today())
                         if season >= PIT_STOPS_FROM else 0)
            print(f"✅ {season}: {races} races, {results} results, {stops} pit stops "
                  f"(network calls so far: {client.network_calls})")


if __name__ == "__main__":
    main()