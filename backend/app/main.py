"""ASGI app factory. Middleware and router registration only - no business logic."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.api.error_handlers import register_error_handlers
from app.api.v1.router import api_v1_router
from app.clients.chat_model_factory import build_chat_model
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.psycopg_dsn import psycopg_dsn
from app.db.session import get_session_factory
from app.graphs.chat.graph import build_chat_agent

# Pool configuration is load-bearing: PostgresSaver requires autocommit and a
# dict-row factory to behave correctly, and misbehaves at runtime rather than
# at import time if either is missing.
_CHAT_POOL_MAX_SIZE = 5


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the chat checkpointer's connection pool for the app's lifetime.

    Not opened at import time (the module-level `graph` in `graphs/chat/graph.py`
    has no checkpointer) because that would make pytest collection, mypy, and
    alembic all try to connect to the database.
    """
    pool: ConnectionPool[Connection[dict[str, Any]]] = ConnectionPool(
        conninfo=psycopg_dsn(get_settings().database_url),
        max_size=_CHAT_POOL_MAX_SIZE,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )
    pool.open()
    try:
        checkpointer = PostgresSaver(pool)
        app.state.chat_agent = build_chat_agent(
            get_session_factory(), build_chat_model(), checkpointer=checkpointer
        )
        yield
    finally:
        pool.close()


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    configure_logging()
    app = FastAPI(title="My Finance API", version="0.1.0", lifespan=_lifespan)
    register_error_handlers(app)
    app.include_router(api_v1_router, prefix="/api/v1")
    return app


app = create_app()
