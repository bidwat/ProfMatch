#!/usr/bin/env python3
"""Copy the local Professor Match SQLite seed DB into Postgres.

Usage:
  DATABASE_URL='postgresql+psycopg://user:pass@host:5432/db' \
    python scripts/migrate_sqlite_to_postgres.py

Optional:
  SQLITE_DB_PATH=db/professor_match_publications.sqlite
  RESET_POSTGRES=true  # delete existing seed/user tables before import
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Type

from dotenv import load_dotenv
from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine, select
from urllib.parse import quote_plus

# Import all table models so SQLModel metadata is complete.
from apps.backend.app.models.auth import AuthSession, User, UserState
from apps.backend.app.models.professor import Professor, Publication
from apps.backend.app.models.scrape_run import ScrapeRun
from apps.backend.app.models.student_profile import StudentProfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE = PROJECT_ROOT / "db" / "professor_match_publications.sqlite"

TABLES: tuple[Type[SQLModel], ...] = (
    Professor,
    Publication,
    User,
    UserState,
    AuthSession,
    ScrapeRun,
    StudentProfile,
)


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def database_url_from_env() -> str:
    raw_url = os.environ.get("DATABASE_URL", "").strip()
    if raw_url:
        return normalize_database_url(raw_url)

    # Prefer pooler settings when present. Supabase direct DB hosts are often
    # IPv6-only on free projects; the session pooler is IPv4-compatible.
    host = os.environ.get("SUPABASE_POOLER_HOST", "").strip() or os.environ.get("SUPABASE_DB_HOST", "").strip()
    password = os.environ.get("SUPABASE_DB_PASSWORD", "")
    if not host or not password:
        return ""
    user = os.environ.get("SUPABASE_POOLER_USER", "").strip() or os.environ.get("SUPABASE_DB_USER", "postgres").strip() or "postgres"
    port = os.environ.get("SUPABASE_POOLER_PORT", "").strip() or os.environ.get("SUPABASE_DB_PORT", "5432").strip() or "5432"
    database = os.environ.get("SUPABASE_DB_NAME", "postgres").strip() or "postgres"
    sslmode = os.environ.get("SUPABASE_DB_SSLMODE", "require").strip() or "require"
    return f"postgresql+psycopg://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{database}?sslmode={quote_plus(sslmode)}"


def copy_table(source: Session, dest: Session, model: Type[SQLModel]) -> int:
    rows = source.exec(select(model)).all()
    for row in rows:
        data = row.model_dump()
        dest.add(model(**data))
    dest.commit()
    return len(rows)


def reset_tables(dest: Session, models: Iterable[Type[SQLModel]]) -> None:
    # Delete child tables first, then parents.
    for model in reversed(tuple(models)):
        table = model.__table__.name  # type: ignore[attr-defined]
        dest.execute(text(f'DELETE FROM "{table}"'))
    dest.commit()


def refresh_postgres_sequences(dest: Session, models: Iterable[Type[SQLModel]]) -> None:
    for model in models:
        table = model.__table__.name  # type: ignore[attr-defined]
        if "id" not in model.__table__.columns:  # type: ignore[attr-defined]
            continue
        dest.execute(text(
            "SELECT setval(pg_get_serial_sequence(:table_name, 'id'), "
            f"COALESCE((SELECT MAX(id) FROM \"{table}\"), 1), true)"
        ), {"table_name": table})
    dest.commit()


def main() -> None:
    load_dotenv()
    postgres_url = database_url_from_env()
    if not postgres_url:
        raise SystemExit("Set DATABASE_URL, or set SUPABASE_DB_HOST and SUPABASE_DB_PASSWORD in .env.")

    sqlite_path = Path(os.environ.get("SQLITE_DB_PATH", DEFAULT_SQLITE)).expanduser().resolve()
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite DB not found: {sqlite_path}")

    source_engine = create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False})
    dest_engine = create_engine(postgres_url, pool_pre_ping=True)

    SQLModel.metadata.create_all(dest_engine)

    with Session(source_engine) as source, Session(dest_engine) as dest:
        if os.environ.get("RESET_POSTGRES", "").lower() in {"1", "true", "yes"}:
            print("Resetting destination tables...")
            reset_tables(dest, TABLES)

        for model in TABLES:
            count = copy_table(source, dest, model)
            print(f"Copied {count:5d} rows: {model.__table__.name}")  # type: ignore[attr-defined]

        if dest_engine.dialect.name == "postgresql":
            refresh_postgres_sequences(dest, TABLES)

    print("Migration complete.")


if __name__ == "__main__":
    main()
