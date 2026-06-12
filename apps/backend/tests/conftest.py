import pytest

from apps.backend.app.db import MemoryDatabase, set_db


@pytest.fixture(autouse=True)
def memory_db():
    """Give every test a fresh in-memory database."""
    database = MemoryDatabase()
    set_db(database)
    yield database
    set_db(None)
