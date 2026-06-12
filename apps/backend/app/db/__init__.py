import os
from pathlib import Path
from urllib.parse import quote_plus

from sqlmodel import Session, create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _normalize_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw_url


def _supabase_database_url() -> str:
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


def is_production_mode() -> bool:
    return os.environ.get("APP_ENV", "").strip().lower() in {"prod", "production"}


def _database_url() -> str:
    """Return the Supabase/Postgres URL. There is no file-based database.

    Without DATABASE_URL or Supabase component vars, non-production processes
    get a private in-memory engine so imports and tests work; production
    refuses to start.
    """
    raw_url = os.environ.get("DATABASE_URL", "").strip()
    if raw_url:
        return _normalize_database_url(raw_url)

    supabase_url = _supabase_database_url()
    if supabase_url:
        return supabase_url

    if is_production_mode():
        raise RuntimeError("APP_ENV=production requires DATABASE_URL or Supabase Postgres variables")

    return "sqlite://"  # in-memory placeholder; tests override `engine`


DATABASE_URL = _database_url()
DB_PATH = None
if DATABASE_URL.startswith("sqlite"):
    # In-memory placeholder needs one shared connection so startup
    # create_all() is visible to request sessions.
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


def get_session():
    with Session(engine) as session:
        yield session
