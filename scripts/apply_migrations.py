#!/usr/bin/env python3
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "supabase" / "migrations"


def apply(url: str | None = None) -> None:
    dsn = url or os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL required")
    files = sorted(MIGRATIONS.glob("*.sql"))
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                  name text PRIMARY KEY,
                  applied_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute("SELECT name FROM schema_migrations")
            applied = {row[0] for row in cur.fetchall()}
            cur.execute("SELECT to_regclass('public.app_users')")
            legacy = cur.fetchone()[0]
            if legacy and "001_initial_schema.sql" not in applied:
                cur.execute("INSERT INTO schema_migrations (name) VALUES ('001_initial_schema.sql')")
                applied.add("001_initial_schema.sql")
            conn.commit()
        for path in files:
            if path.name in applied:
                continue
            sql = path.read_text()
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
            conn.commit()
            print(f"applied {path.name}")
    print("migrations up to date")


if __name__ == "__main__":
    apply()
