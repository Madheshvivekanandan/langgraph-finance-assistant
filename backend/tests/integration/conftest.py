"""Fixtures for tests that touch a real database.

These run against the dedicated test database set up in tests/conftest.py, never
the development one. Each test starts and ends with empty tables.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

import app.main as main_module
from app.core.config import get_settings
from app.db.psycopg_dsn import psycopg_dsn
from app.db.session import get_session_factory
from app.main import create_app
from tests.fakes.fake_category_suggester import FakeCategorySuggester


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
def category_suggester() -> FakeCategorySuggester:
    """The suggester the `client` fixture's app is built on.

    A fixture rather than a literal so a module that wants different model
    behaviour - a confidence below the review threshold, say - can override it
    by defining `category_suggester` of its own.
    """
    return FakeCategorySuggester()


@pytest.fixture
def client(
    session_factory: sessionmaker[Session],
    category_suggester: FakeCategorySuggester,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    """An API client sharing the cleaned database, and never calling a real model.

    The lifespan builds the statement graph from `build_category_suggester()`,
    which returns a live OpenAI client whenever a developer has a key in `.env`.
    That made the suite non-deterministic: a real prediction below the review
    threshold pauses the run, so nothing is stored and tests that only wanted to
    upload a statement find no rows. Substituting the fake at its source keeps
    the graph, the checkpointer, and the wiring real while the one non-local
    dependency is not.
    """
    _ = session_factory  # ordering dependency: tables are cleaned before the app runs
    monkeypatch.setattr(main_module, "build_category_suggester", lambda: category_suggester)
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def chat_checkpointer() -> Iterator[PostgresSaver]:
    """A real `PostgresSaver` against the test database.

    Its tables were already created by `_setup_test_checkpointer` in
    tests/conftest.py; this fixture only opens a connection to them.
    """
    with PostgresSaver.from_conn_string(psycopg_dsn(get_settings().database_url)) as saver:
        yield saver


@pytest.fixture
def statement_checkpointer() -> Iterator[PostgresSaver]:
    """A real `PostgresSaver` for the statement graph, against the test database.

    Same body as `chat_checkpointer`: the checkpointer tables are shared across
    every graph in this app, so there is nothing statement-specific to set up.
    """
    with PostgresSaver.from_conn_string(psycopg_dsn(get_settings().database_url)) as saver:
        yield saver
