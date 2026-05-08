import os
from pathlib import Path
from sqlmodel import Session, create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DB_PATH = PROJECT_ROOT / "db" / "professor_match_publications.sqlite"
DB_PATH = Path(os.environ.get("PROFESSOR_MATCH_DB_PATH", DEFAULT_DB_PATH)).expanduser().resolve()
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False)


def get_session():
    with Session(engine) as session:
        yield session