"""Test-wide setup: redirect every test at a dedicated database.

Imported by pytest before any test module, so the environment is rewritten
before `app.core.config` is ever read. Without this the suite would run against
the development database and its TRUNCATEs would destroy real uploads.
"""

import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_DIR.parent
_TEST_DB_SUFFIX = "_test"


def _derive_test_url(database_url: str) -> str:
    """Return the same server and credentials, but the `<name>_test` database."""
    parts = urlsplit(database_url)
    name = parts.path.lstrip("/")
    if name.endswith(_TEST_DB_SUFFIX):
        return database_url
    return urlunsplit(parts._replace(path=f"/{name}{_TEST_DB_SUFFIX}"))


def _maintenance_url(database_url: str) -> str:
    """Return a URL for the always-present `postgres` database on the same server."""
    return urlunsplit(urlsplit(database_url)._replace(path="/postgres"))


def _database_name(database_url: str) -> str:
    return urlsplit(database_url).path.lstrip("/")


# Runs at import time - before any app module reads its settings.
load_dotenv(_REPO_ROOT / ".env")
_DEV_URL = os.environ.get("DATABASE_URL")
if not _DEV_URL:
    raise RuntimeError("DATABASE_URL is not set; copy .env.example to .env first")
TEST_DATABASE_URL = _derive_test_url(_DEV_URL)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


def _create_test_database_if_missing() -> None:
    """Create the test database if this is the first run on a fresh volume."""
    name = _database_name(TEST_DATABASE_URL)
    engine = create_engine(_maintenance_url(_DEV_URL), isolation_level="AUTOCOMMIT")
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
        ).scalar_one_or_none()
        if exists is None:
            # Identifier cannot be bound as a parameter; it is derived from our own
            # DATABASE_URL, not from user input.
            connection.execute(text(f'CREATE DATABASE "{name}"'))
    engine.dispose()


def _migrate_test_database() -> None:
    """Bring the test database up to head, so tests see the real schema."""
    from alembic import command
    from alembic.config import Config

    from app.core.config import get_settings

    # The settings singleton may have been built before the redirect above.
    get_settings.cache_clear()

    config = Config(str(_BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(_BACKEND_DIR / "app" / "db" / "migrations"))
    command.upgrade(config, "head")


def _setup_test_checkpointer() -> None:
    """Create the LangGraph checkpointer's tables on the test database.

    Same code path as the compose `migrate` one-shot (`app.db.checkpointer_setup`),
    run against `myfinance_test` right after Alembic - so there is exactly one
    way these tables ever get created, in dev and in tests alike.
    """
    from app.db.checkpointer_setup import setup_checkpointer

    setup_checkpointer(TEST_DATABASE_URL)


@pytest.fixture(scope="session", autouse=True)
def _prepared_test_database() -> None:
    """Guarantee a migrated test database exists before the first test runs."""
    _create_test_database_if_missing()
    _migrate_test_database()
    _setup_test_checkpointer()
