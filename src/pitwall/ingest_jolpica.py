"""Turn Jolpica JSON into rows in our tables, using idempotent upserts."""

from datetime import date

from pitwall.jolpica import JolpicaClient


def parse_duration(text: str | None) -> float | None:
    """'23.456' -> 23.456 ; '1:02.345' -> 62.345 ; '' or None -> None (duration not recorded)."""
    if not text:
        return None
    if ":" in text:
        minutes, seconds = text.split(":")
        return int(minutes) * 60 + float(seconds)
    return float(text)


def _int(value):
    """Jolpica sends numbers as strings; missing stays None."""
    return int(value) if value not in (None, "") else None


def load_schedule(client: JolpicaClient, cur, season: int) -> int:
    count = 0
    for mr in client.pages(f"{season}/races/", season):
        for race in mr["RaceTable"]["Races"]:
            cur.execute(
                """INSERT INTO races (season, round, name, circuit, race_date)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (season, round) DO UPDATE
                   SET name = EXCLUDED.name, circuit = EXCLUDED.circuit,
                       race_date = EXCLUDED.race_date""",
                (int(race["season"]), int(race["round"]), race["raceName"],
                 race["Circuit"]["circuitName"], race["date"]),
            )
            count += 1
    return count


def load_results(client: JolpicaClient, cur, season: int) -> int:
    race_ids = dict(
        cur.execute("SELECT round, race_id FROM races WHERE season = %s", (season,)).fetchall()
    )
    count = 0
    for mr in client.pages(f"{season}/results/", season):
        for race in mr["RaceTable"]["Races"]:
            race_id = race_ids[int(race["round"])]
            for r in race["Results"]:
                d, c = r["Driver"], r["Constructor"]
                cur.execute(
                    """INSERT INTO drivers (driver_id, code, given_name, family_name, number, nationality)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT (driver_id) DO UPDATE
                       SET code = EXCLUDED.code, number = EXCLUDED.number""",
                    (d["driverId"], d.get("code"), d["givenName"], d["familyName"],
                     _int(d.get("permanentNumber")), d.get("nationality")),
                )
                cur.execute(
                    """INSERT INTO constructors (constructor_id, name, nationality)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (constructor_id) DO UPDATE SET name = EXCLUDED.name""",
                    (c["constructorId"], c["name"], c.get("nationality")),
                )
                cur.execute(
                    """INSERT INTO results (race_id, driver_id, constructor_id, grid, position,
                                            position_text, points, status, laps)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (race_id, driver_id) DO UPDATE
                       SET constructor_id = EXCLUDED.constructor_id, grid = EXCLUDED.grid,
                           position = EXCLUDED.position, position_text = EXCLUDED.position_text,
                           points = EXCLUDED.points, status = EXCLUDED.status, laps = EXCLUDED.laps""",
                    (race_id, d["driverId"], c["constructorId"], _int(r.get("grid")),
                     _int(r.get("position")), r.get("positionText"), r.get("points"),
                     r.get("status"), _int(r.get("laps"))),
                )
                count += 1
    return count


def load_pit_stops(client: JolpicaClient, cur, season: int, today: date) -> int:
    # Only races that have already happened; future races would waste calls.
    races = cur.execute(
        "SELECT round, race_id FROM races WHERE season = %s AND race_date <= %s ORDER BY round",
        (season, today),
    ).fetchall()
    count = 0
    for rnd, race_id in races:
        for mr in client.pages(f"{season}/{rnd}/pitstops/", season):
            for race in mr["RaceTable"]["Races"]:
                for p in race["PitStops"]:
                    cur.execute(
                        """INSERT INTO pit_stops (race_id, driver_id, stop_no, lap, duration_s)
                           VALUES (%s, %s, %s, %s, %s)
                           ON CONFLICT (race_id, driver_id, stop_no) DO UPDATE
                           SET lap = EXCLUDED.lap, duration_s = EXCLUDED.duration_s""",
                        (race_id, p["driverId"], int(p["stop"]), int(p["lap"]),
                         parse_duration(p["duration"])),
                    )
                    count += 1
    return count