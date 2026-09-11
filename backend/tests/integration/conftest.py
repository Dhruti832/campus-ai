"""Shared fixtures for integration tests that need a real Postgres+pgvector.

These tests assume the schema from infra/init-db/001_enable_pgvector.sql
has already been applied (docker compose does this automatically). If no
database is reachable, tests here are skipped rather than failed, so the
unit test suite stays runnable without Docker.
"""

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://unichat:unichat@localhost:5432/unichat",
)


@pytest.fixture(scope="session")
def pg_engine():
    engine = create_engine(TEST_DATABASE_URL)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        pytest.skip(
            f"No Postgres reachable at {TEST_DATABASE_URL} — start `docker compose up postgres`"
        )
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(pg_engine):
    session = Session(bind=pg_engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()
