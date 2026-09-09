"""Translate a SQLAlchemy database URL into a psycopg-native DSN."""

import re

_DRIVER_SUFFIX = re.compile(r"^postgresql\+[^:]+://")


def psycopg_dsn(database_url: str) -> str:
    """Strip the SQLAlchemy `+driver` suffix so psycopg can parse the URL.

    `settings.database_url` is `postgresql+psycopg://...` for SQLAlchemy;
    psycopg itself (used directly by `PostgresSaver` and its connection pool)
    only understands the bare `postgresql://` scheme.
    """
    return _DRIVER_SUFFIX.sub("postgresql://", database_url)
