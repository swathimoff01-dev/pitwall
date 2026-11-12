import psycopg
import pytest

from pitwall.config import get_settings


RECONCILE_SQL = """
WITH m AS (
  SELECT r.season, r.name, x.driver_id, x.status, x.laps AS j, count(l.lap_no) AS o,
         bool_or(l.lap_no = x.laps + 1 AND l.lap_time_s IS NULL) AS extra_untimed
  FROM results x
  JOIN races r USING (race_id)
  LEFT JOIN laps l USING (race_id, driver_id)
  WHERE r.season >= 2023
  GROUP BY 1, 2, 3, 4, 5
)
SELECT season, name, driver_id, status, j, o FROM m
WHERE o <> j
  AND NOT (o - j = 1 AND coalesce(extra_untimed, false))   -- final untimed lap where the car stopped
  AND NOT (status = 'Disqualified' AND j = 0)               -- Jolpica wipes laps for DSQ
  AND (season, name) NOT IN (SELECT season, race_name FROM known_data_issues
                             WHERE table_name = 'laps')     -- documented source gaps
"""


def test_laps_reconcile_with_jolpica():
    with psycopg.connect(get_settings().agent_conninfo()) as conn:
        if conn.execute("SELECT count(*) FROM laps").fetchone()[0] == 0:
            pytest.skip("laps is empty; load data first")
        unexplained = conn.execute(RECONCILE_SQL).fetchall()
    assert unexplained == [], f"Unexplained lap-count mismatches: {unexplained[:10]}"
    
MIN_SEASON_SQL = {
    "races": "SELECT min(season) FROM races",
    "results": "SELECT min(r.season) FROM results x JOIN races r USING (race_id)",
    "pit_stops": "SELECT min(r.season) FROM pit_stops x JOIN races r USING (race_id)",
    "laps": "SELECT min(r.season) FROM laps x JOIN races r USING (race_id)",
    "stints": "SELECT min(r.season) FROM stints x JOIN races r USING (race_id)",
    "race_control_messages": "SELECT min(r.season) FROM race_control_messages x JOIN races r USING (race_id)",
    "regulation_articles": "SELECT min(season) FROM regulation_articles",
        "stewards_decisions": "SELECT min(season) FROM stewards_decisions",
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