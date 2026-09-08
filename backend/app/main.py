"""ASGI app factory. Middleware and router registration only - no business logic."""

from fastapi import FastAPI

from app.api.error_handlers import register_error_handlers
from app.api.v1.router import api_v1_router
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    """Build the FastAPI application."""
    configure_logging()
    app = FastAPI(title="My Finance API", version="0.1.0")
    register_error_handlers(app)
    app.include_router(api_v1_router, prefix="/api/v1")
    return app


app = create_app()
