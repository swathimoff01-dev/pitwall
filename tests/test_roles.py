"""Prove the roles can do exactly what we promised, and no more."""

import psycopg
import pytest
from psycopg import errors

from pitwall.config import get_settings


@pytest.fixture
def agent():
    with psycopg.connect(get_settings().agent_conninfo(), autocommit=True) as conn:
        yield conn


@pytest.fixture
def agent_sign_off(agent):
    """Agent session with the read-only 'sign' removed, so only GRANTs are being tested."""
    agent.execute("SET default_transaction_read_only = off")
    return agent


@pytest.fixture
def publisher():
    conn = psycopg.connect(get_settings().publisher_conninfo())
    try:
        yield conn
    finally:
        conn.rollback()  # never leave test rows behind
        conn.close()


def test_agent_can_read(agent):
    assert agent.execute("SELECT count(*) FROM races").fetchone()[0] >= 0


def test_agent_can_use_vector_operators(agent):
    # Orthogonal vectors have cosine distance 1
    dist = agent.execute("SELECT '[1,0]'::vector <=> '[0,1]'::vector").fetchone()[0]
    assert dist == pytest.approx(1.0)


def test_agent_is_read_only_by_default(agent):
    assert agent.execute("SHOW default_transaction_read_only").fetchone()[0] == "on"


def test_agent_cannot_insert_even_with_sign_off(agent_sign_off):
    with pytest.raises(errors.InsufficientPrivilege):
        agent_sign_off.execute(
            "INSERT INTO races (season, round, name) VALUES (2025, 1, 'x')"
        )


def test_agent_cannot_drop_tables(agent_sign_off):
    with pytest.raises(errors.InsufficientPrivilege):
        agent_sign_off.execute("DROP TABLE races")


def test_agent_cannot_write_rulings(agent_sign_off):
    with pytest.raises(errors.InsufficientPrivilege):
        agent_sign_off.execute("INSERT INTO rulings (incident, draft) VALUES ('x', '{}')")


def test_publisher_can_write_rulings(publisher):
    row = publisher.execute(
        "INSERT INTO rulings (incident, draft) VALUES ('test', '{}') RETURNING ruling_id"
    ).fetchone()
    assert row[0] is not None


def test_publisher_cannot_touch_race_data(publisher):
    with pytest.raises(errors.InsufficientPrivilege):
        publisher.execute("INSERT INTO races (season, round, name) VALUES (2025, 1, 'x')")
