"""Translate domain errors into RFC 9457 problem+json responses.

This is the only layer that knows about HTTP status codes; services raise
domain exceptions and stay unaware of the transport.
"""

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    AppError,
    DuplicateStatementError,
    InvalidPageTokenError,
    StatementNotFoundError,
    StatementParseError,
)
from app.schemas.problem_detail import ProblemDetail

logger = logging.getLogger(__name__)

PROBLEM_MEDIA_TYPE = "application/problem+json"
_PROBLEM_BASE_URI = "https://my-finance.local/problems/"


def _problem(*, status: int, code: str, title: str, detail: str) -> JSONResponse:
    """Build a problem+json response with a stable machine-readable code."""
    body = ProblemDetail(
        type=f"{_PROBLEM_BASE_URI}{code.lower().replace('_', '-')}",
        title=title,
        status=status,
        detail=detail,
        code=code,
    )
    return JSONResponse(
        status_code=status, content=body.model_dump(), media_type=PROBLEM_MEDIA_TYPE
    )


def register_error_handlers(app: FastAPI) -> None:
    """Attach one handler per domain error class, plus a catch-all."""

    @app.exception_handler(DuplicateStatementError)
    async def _duplicate(_: Request, exc: DuplicateStatementError) -> Response:
        return _problem(
            status=409,
            code="STATEMENT_ALREADY_UPLOADED",
            title="Statement already uploaded",
            detail=str(exc),
        )

    @app.exception_handler(StatementParseError)
    async def _parse_failed(_: Request, exc: StatementParseError) -> Response:
        return _problem(
            status=422,
            code="STATEMENT_UNREADABLE",
            title="Statement could not be read",
            detail=str(exc),
        )

    @app.exception_handler(StatementNotFoundError)
    async def _not_found(_: Request, exc: StatementNotFoundError) -> Response:
        return _problem(
            status=404,
            code="STATEMENT_NOT_FOUND",
            title="Statement not found",
            detail=str(exc),
        )

    @app.exception_handler(InvalidPageTokenError)
    async def _bad_token(_: Request, exc: InvalidPageTokenError) -> Response:
        return _problem(
            status=400,
            code="INVALID_PAGE_TOKEN",
            title="Invalid page token",
            detail=str(exc),
        )

    @app.exception_handler(AppError)
    async def _unexpected(_: Request, exc: AppError) -> Response:
        # Log the cause; tell the client nothing about our internals.
        logger.error("unhandled_application_error", exc_info=exc)
        return _problem(
            status=500,
            code="INTERNAL_ERROR",
            title="Internal server error",
            detail="The request could not be completed.",
        )

    # Referenced so linters see the handlers as used; FastAPI holds the real refs.
    _handlers: tuple[Callable[..., Awaitable[Response]], ...] = (
        _duplicate,
        _parse_failed,
        _not_found,
        _bad_token,
        _unexpected,
    )
    logger.debug("registered %d domain error handlers", len(_handlers))
