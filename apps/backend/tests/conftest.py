import pytest
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture()
def db_session(tmp_path):
    db_path = tmp_path / "test_match.sqlite"
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
