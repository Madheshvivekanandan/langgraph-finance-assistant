"""FastAPI dependencies: build services and hand them to routes."""

from typing import Annotated

from fastapi import Depends, Request

from app.db.session import get_session_factory
from app.graphs.statement.graph import graph as statement_graph
from app.services.chat_service import ChatService
from app.services.statement_ingestion_service import StatementIngestionService
from app.services.statement_query_service import StatementQueryService
from app.services.summary_service import SummaryService
from app.services.transaction_category_service import TransactionCategoryService
from app.services.transaction_query_service import TransactionQueryService


def get_statement_ingestion_service() -> StatementIngestionService:
    """Build the ingestion service around the shared graph and session factory."""
    return StatementIngestionService(get_session_factory(), statement_graph)


def get_statement_query_service() -> StatementQueryService:
    """Build the statement read service."""
    return StatementQueryService(get_session_factory())


def get_summary_service() -> SummaryService:
    """Build the dashboard aggregate service."""
    return SummaryService(get_session_factory())


def get_transaction_category_service() -> TransactionCategoryService:
    """Build the service that applies a person's category corrections."""
    return TransactionCategoryService(get_session_factory())


def get_transaction_query_service() -> TransactionQueryService:
    """Build the transaction read service."""
    return TransactionQueryService(get_session_factory())


def get_chat_service(request: Request) -> ChatService:
    """Wrap the checkpointed agent the lifespan built, on `app.state.chat_agent`.

    Read from `request.app.state` rather than built here: the checkpointed
    agent owns a live `psycopg_pool.ConnectionPool` opened once at startup, not
    per-request.
    """
    return ChatService(request.app.state.chat_agent)


StatementIngestionServiceDep = Annotated[
    StatementIngestionService, Depends(get_statement_ingestion_service)
]
StatementQueryServiceDep = Annotated[StatementQueryService, Depends(get_statement_query_service)]
SummaryServiceDep = Annotated[SummaryService, Depends(get_summary_service)]
TransactionCategoryServiceDep = Annotated[
    TransactionCategoryService, Depends(get_transaction_category_service)
]
TransactionQueryServiceDep = Annotated[
    TransactionQueryService, Depends(get_transaction_query_service)
]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
