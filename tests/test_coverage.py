import psycopg
import pytest

from pitwall.config import get_settings

MIN_SEASON_SQL = {
    "races": "SELECT min(season) FROM races",
    "results": "SELECT min(r.season) FROM results x JOIN races r USING (race_id)",
    "pit_stops": "SELECT min(r.season) FROM pit_stops x JOIN races r USING (race_id)",
}


@pytest.mark.parametrize("table", MIN_SEASON_SQL)
def test_coverage_matches_loaded_data(table):
    with psycopg.connect(get_settings().agent_conninfo()) as conn:
        actual = conn.execute(MIN_SEASON_SQL[table]).fetchone()[0]
        if actual is None:
            pytest.skip(f"{table} is empty; load data first")
        claimed = conn.execute(
            "SELECT first_season FROM data_coverage WHERE table_name = %s", (table,)
        ).fetchone()[0]
    assert actual == claimed