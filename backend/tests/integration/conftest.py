"""Fixtures for tests that touch a real database.

These run against the dedicated test database set up in tests/conftest.py, never
the development one. Each test starts and ends with empty tables.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_session_factory
from app.main import create_app


def _assert_is_test_database(factory: sessionmaker[Session]) -> None:
    """Refuse to truncate anything that is not the test database.

    Defence in depth: the redirect in tests/conftest.py is what points the suite
    at the right database, but a mistake there previously wiped real uploads, so
    the destructive operation checks for itself.
    """
    with factory() as session:
        name = session.execute(text("SELECT current_database()")).scalar_one()
    if not str(name).endswith("_test"):
        raise RuntimeError(
            f"refusing to truncate {name!r}: integration tests must run against a "
            "database whose name ends in '_test'"
        )


def _truncate_all(factory: sessionmaker[Session]) -> None:
    """Empty both tables; CASCADE covers the transactions foreign key."""
    _assert_is_test_database(factory)
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
