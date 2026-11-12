"""Turn OpenF1 JSON into rows in our tables."""

from datetime import date, datetime, timedelta, timezone
# from datetime import date, datetime, 
from pitwall.openf1 import OpenF1Client

def utc_race_date(session: dict) -> date:
    return datetime.fromisoformat(session["date_start"]).astimezone(timezone.utc).date()

def find_race_id(races: dict[date, int], start: date) -> int | None:
    """Races are at least a week apart, so a +/- 1 day window is safe and time-zone proof."""
    hits = [rid for d, rid in races.items() if abs((d - start).days) <= 1]
    return hits[0] if len(hits) == 1 else None

def local_race_date(session: dict) -> date:
    """UTC start shifted by the track's UTC offset = the local calendar date Jolpica uses."""
    start = datetime.fromisoformat(session["date_start"])
    offset = session["gmt_offset"]
    sign = -1 if offset.startswith("-") else 1
    hours, minutes, seconds = (int(part) for part in offset.lstrip("+-").split(":"))
    return (start + sign * timedelta(hours=hours, minutes=minutes, seconds=seconds)).date()


def match_driver(candidates: list, acronym: str, last_name: str | None) -> str | None:
    """candidates: (driver_id, code, family_name) of drivers who have a result in this race."""
    by_code = [c[0] for c in candidates if c[1] == acronym]
    if len(by_code) == 1:
        return by_code[0]
    by_name = [c[0] for c in candidates if c[2].casefold() == (last_name or "").casefold()]
    return by_name[0] if len(by_name) == 1 else None


def stint_for_lap(stints: list[dict], lap: int) -> dict | None:
    for s in stints:
        end = s["lap_end"] if s["lap_end"] is not None else 10**6  # last stint can be open-ended
        if s["lap_start"] <= lap <= end:
            return s
    return None


def tyre_life(stint: dict, lap: int) -> int:
    """Laps on this set of tyres including the current lap."""
    return (stint["tyre_age_at_start"] or 0) + (lap - stint["lap_start"]) + 1


def load_race(client: OpenF1Client, cur, season: int, race_id: int, session_key: int):
    candidates = cur.execute(
        """SELECT d.driver_id, d.code, d.family_name
           FROM results x JOIN drivers d USING (driver_id)
           WHERE x.race_id = %s""",
        (race_id,),
    ).fetchall()

    by_number: dict[int, str] = {}
    for d in client.get("drivers", season, session_key=session_key):
        driver_id = match_driver(candidates, d["name_acronym"], d.get("last_name"))
        if driver_id is None:
            print(f"⚠️  race {race_id}: no match for {d.get('full_name')} "
                  f"({d['name_acronym']}); their rows are skipped")
            continue
        by_number[d["driver_number"]] = driver_id

    # ---- stints ----
    stints_by_driver: dict[str, list[dict]] = {}
    n_stints = 0
    for s in client.get("stints", season, session_key=session_key):
        driver_id = by_number.get(s["driver_number"])
        if driver_id is None:
            continue
        stints_by_driver.setdefault(driver_id, []).append(s)
        cur.execute(
            """INSERT INTO stints (race_id, driver_id, stint_no, compound, start_lap, end_lap,
                                   tyre_age_at_start)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (race_id, driver_id, stint_no) DO UPDATE
               SET compound = EXCLUDED.compound, start_lap = EXCLUDED.start_lap,
                   end_lap = EXCLUDED.end_lap, tyre_age_at_start = EXCLUDED.tyre_age_at_start""",
            (race_id, driver_id, s["stint_number"], s["compound"], s["lap_start"],
             s["lap_end"], s["tyre_age_at_start"]),
        )
        n_stints += 1

    # ---- laps (compound, stint and tyre life are derived from the stints above) ----
    n_laps = 0
    for lap in client.get("laps", season, session_key=session_key):
        driver_id = by_number.get(lap["driver_number"])
        if driver_id is None or lap["lap_number"] is None:
            continue
        stint = stint_for_lap(stints_by_driver.get(driver_id, []), lap["lap_number"])
        cur.execute(
            """INSERT INTO laps (race_id, driver_id, lap_no, lap_time_s, sector1_s, sector2_s,
                                 sector3_s, compound, tyre_life, stint_no, is_pit_out_lap)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (race_id, driver_id, lap_no) DO UPDATE
               SET lap_time_s = EXCLUDED.lap_time_s, sector1_s = EXCLUDED.sector1_s,
                   sector2_s = EXCLUDED.sector2_s, sector3_s = EXCLUDED.sector3_s,
                   compound = EXCLUDED.compound, tyre_life = EXCLUDED.tyre_life,
                   stint_no = EXCLUDED.stint_no, is_pit_out_lap = EXCLUDED.is_pit_out_lap""",
            (race_id, driver_id, lap["lap_number"], lap["lap_duration"],
             lap["duration_sector_1"], lap["duration_sector_2"], lap["duration_sector_3"],
             stint["compound"] if stint else None,
             tyre_life(stint, lap["lap_number"]) if stint else None,
             stint["stint_number"] if stint else None,
             lap["is_pit_out_lap"]),
        )
        n_laps += 1

    # ---- race control messages: replace this race's messages so reruns never duplicate ----
    cur.execute("DELETE FROM race_control_messages WHERE race_id = %s", (race_id,))
    n_msgs = 0
    for m in client.get("race_control", season, session_key=session_key):
        cur.execute(
            """INSERT INTO race_control_messages (race_id, lap, ts, category, flag, message,
                                                  scope, sector, driver_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (race_id, m["lap_number"], m["date"], m["category"], m["flag"], m["message"],
             m["scope"], m["sector"], by_number.get(m["driver_number"])),
        )
        n_msgs += 1
    return n_laps, n_stints, n_msgs


def load_season(client: OpenF1Client, cur, season: int) -> tuple[int, int, int, int]:
    race_ids = {
        d: rid for d, rid in
        cur.execute("SELECT race_date, race_id FROM races WHERE season = %s", (season,)).fetchall()
    }
    sessions = [s for s in client.get("sessions", season, year=season, session_name="Race")
                if not s.get("is_cancelled")]
    if not sessions:
        print(f"ℹ️  {season}: OpenF1 has no race sessions for this season")
    totals = [0, 0, 0, 0]
    for sess in sessions:
        start = utc_race_date(sess)
        race_id = find_race_id(race_ids, start)
        if race_id is None:
            raise RuntimeError(
                f"No race in our database within a day of {start} "
                f"for OpenF1 session {sess['session_key']} ({sess['location']})"
            )
        laps, stints, msgs = load_race(client, cur, season, race_id, sess["session_key"])
        totals = [totals[0] + 1, totals[1] + laps, totals[2] + stints, totals[3] + msgs]
    return tuple(totals)