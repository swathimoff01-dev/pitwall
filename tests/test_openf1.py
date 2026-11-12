from datetime import date

from pitwall.ingest_openf1 import find_race_id, match_driver, stint_for_lap, tyre_life, utc_race_date

# ---- matching OpenF1 sessions to our races ----

RACES = {date(2023, 11, 18): 21, date(2023, 11, 26): 22}


def test_utc_date_las_vegas_night_race():
    # Starts Saturday 22:00 local, which is already Sunday 06:00 UTC
    assert utc_race_date({"date_start": "2023-11-19T06:00:00+00:00"}) == date(2023, 11, 19)


def test_find_race_tolerates_one_day_either_way():
    assert find_race_id(RACES, date(2023, 11, 19)) == 21
    assert find_race_id(RACES, date(2023, 11, 25)) == 22


def test_find_race_no_match():
    assert find_race_id(RACES, date(2023, 12, 10)) is None


# ---- matching OpenF1 drivers to our drivers ----

CANDIDATES = [("max_verstappen", "VER", "Verstappen"), ("perez", "PER", "Pérez")]


def test_match_by_code():
    assert match_driver(CANDIDATES, "VER", "Verstappen") == "max_verstappen"


def test_match_falls_back_to_last_name():
    assert match_driver(CANDIDATES, "XXX", "verstappen") == "max_verstappen"


def test_no_match_returns_none():
    assert match_driver(CANDIDATES, "XXX", "Nobody") is None


# ---- deriving tyre data for each lap from stints ----

STINTS = [
    {"stint_number": 1, "lap_start": 1, "lap_end": 18, "tyre_age_at_start": 0},
    {"stint_number": 2, "lap_start": 19, "lap_end": None, "tyre_age_at_start": 2},
]


def test_stint_for_lap_finds_the_right_stint():
    assert stint_for_lap(STINTS, 18)["stint_number"] == 1
    assert stint_for_lap(STINTS, 19)["stint_number"] == 2


def test_open_ended_last_stint():
    assert stint_for_lap(STINTS, 60)["stint_number"] == 2


def test_tyre_life_counts_laps_on_the_set():
    assert tyre_life(STINTS[0], 1) == 1
    assert tyre_life(STINTS[1], 19) == 3  # set already had 2 laps on it
    assert tyre_life(STINTS[1], 20) == 4