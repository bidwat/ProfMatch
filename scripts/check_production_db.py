#!/usr/bin/env python3
"""Validate production DB configuration and baseline Professor Match data.

Intended for deployed/Droplet production checks. It refuses SQLite in
APP_ENV=production and verifies the expected Supabase/Postgres corpus is present.
"""

import os
import sys

from sqlalchemy import text

# Import after env is set so db module can enforce production guardrails.
from apps.backend.app.db import DATABASE_URL, engine, is_production_mode

MIN_PROFESSORS = int(os.environ.get("MIN_PROFESSOR_COUNT", "1000"))
MIN_PUBLICATIONS = int(os.environ.get("MIN_PUBLICATION_COUNT", "4000"))

REQUIRED_TABLES = {
    "professors",
    "publications",
    "users",
    "auth_sessions",
    "user_states",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if not is_production_mode():
        fail("APP_ENV must be production/prod for production DB checks")
    if DATABASE_URL.startswith("sqlite"):
        fail("Production selected SQLite; expected Supabase/Postgres DATABASE_URL")
    if not DATABASE_URL.startswith("postgresql+psycopg"):
        fail(f"Unexpected DATABASE_URL driver: {DATABASE_URL.split(':', 1)[0]}")

    with engine.connect() as conn:
        tables = set(conn.execute(text("select tablename from pg_tables where schemaname = 'public'")))
        table_names = {row[0] for row in tables}
        missing = sorted(REQUIRED_TABLES - table_names)
        if missing:
            fail(f"Missing required tables: {', '.join(missing)}")

        professor_count = int(conn.execute(text("select count(*) from professors")).scalar() or 0)
        publication_count = int(conn.execute(text("select count(*) from publications")).scalar() or 0)

    if professor_count < MIN_PROFESSORS:
        fail(f"Professor count {professor_count} below minimum {MIN_PROFESSORS}")
    if publication_count < MIN_PUBLICATIONS:
        fail(f"Publication count {publication_count} below minimum {MIN_PUBLICATIONS}")

    print("PASS: production DB is Postgres and baseline data is present")
    print(f"professors={professor_count} publications={publication_count}")


if __name__ == "__main__":
    main()
