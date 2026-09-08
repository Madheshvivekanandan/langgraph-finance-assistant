"""Fixtures for tests that touch the real database.

These need the compose Postgres running (`docker compose up -d postgres`) with
migrations applied. Each test starts and ends with empty tables.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_session_factory
from app.main import create_app


def _truncate_all(factory: sessionmaker[Session]) -> None:
    """Empty both tables; CASCADE covers the transactions foreign key."""
    with factory() as session, session.begin():
        session.execute(text("TRUNCATE TABLE transactions, statements RESTART IDENTITY CASCADE"))


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    """A session factory against a database emptied before and after the test."""
    factory = get_session_factory()
    _truncate_all(factory)
    yield factory
    _truncate_all(factory)


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    """An API client sharing the cleaned database."""
    _ = session_factory  # ordering dependency: tables are cleaned before the app runs
    with TestClient(create_app()) as test_client:
        yield test_client
