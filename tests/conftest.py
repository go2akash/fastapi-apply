"""
Test configuration — creates a fresh in-memory SQLite DB for every test.

Why?
- Tests must NEVER touch the real database (app.db)
- Each test gets a clean DB — no leftover data from previous runs
- In-memory DB is fast and disappears after tests finish

How it works:
1. Create a separate SQLAlchemy engine pointing to in-memory SQLite
2. Create all tables using Base.metadata (no need for alembic in tests)
3. Override FastAPI's get_db dependency to use the test DB
4. After each test, drop all tables → clean slate
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.config.database import Base, get_db
from app.main import app

# In-memory SQLite — exists only while tests run, then vanishes
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(TEST_DATABASE_URL)
TestSession = sessionmaker(bind=test_engine)


def override_get_db():
    """Replacement for app's get_db — uses test database instead."""
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


# Tell FastAPI: when any endpoint asks for get_db, give it test DB instead
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """
    Runs before EVERY test automatically (autouse=True).
    Creates all tables → runs test → drops all tables.
    """
    Base.metadata.create_all(bind=test_engine)  # create tables
    yield                                        # test runs here
    Base.metadata.drop_all(bind=test_engine)     # clean up after test


@pytest.fixture
def client():
    """Provides a TestClient for making HTTP requests in tests."""
    return TestClient(app)
