"""Create the agent/publisher roles, then apply any pending SQL migrations."""

from pathlib import Path

import psycopg
from psycopg import sql

from pitwall.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def ensure_role(cur: psycopg.Cursor, user: str, password: str) -> None:
    """CREATE the role if missing, otherwise ALTER it (so password changes in .env apply)."""
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (user,))
    verb = "ALTER" if cur.fetchone() else "CREATE"
    # CREATE ROLE can't take %s placeholders, so we use psycopg's safe quoting helpers.
    cur.execute(
        sql.SQL("{} ROLE {} LOGIN PASSWORD {}").format(
            sql.SQL(verb), sql.Identifier(user), sql.Literal(password)
        )
    )


def main() -> None:
    s = get_settings()
    with psycopg.connect(s.admin_conninfo()) as conn:
        with conn.cursor() as cur:
            ensure_role(cur, s.agent_user, s.agent_password.get_secret_value())
            ensure_role(cur, s.publisher_user, s.publisher_password.get_secret_value())
            cur.execute(
                "CREATE TABLE IF NOT EXISTS public.schema_migrations ("
                " version TEXT PRIMARY KEY,"
                " applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
            )
            cur.execute("SELECT version FROM public.schema_migrations")
            done = {row[0] for row in cur.fetchall()}
        conn.commit()

        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in done:
                print(f"⏭️  {path.name} (already applied)")
                continue
            with conn.transaction():  # all-or-nothing for each file
                conn.execute(path.read_text(encoding="utf-8"))
                conn.execute(
                    "INSERT INTO public.schema_migrations (version) VALUES (%s)",
                    (path.name,),
                )
            print(f"✅ applied {path.name}")


if __name__ == "__main__":
    main()