"""FastAPI dependencies: build services and hand them to routes."""

from typing import Annotated

from fastapi import Depends

from app.db.session import get_session_factory
from app.graphs.statement.graph import graph as statement_graph
from app.services.statement_ingestion_service import StatementIngestionService
from app.services.statement_query_service import StatementQueryService
from app.services.transaction_category_service import TransactionCategoryService
from app.services.transaction_query_service import TransactionQueryService


def get_statement_ingestion_service() -> StatementIngestionService:
    """Build the ingestion service around the shared graph and session factory."""
    return StatementIngestionService(get_session_factory(), statement_graph)


def get_statement_query_service() -> StatementQueryService:
    """Build the statement read service."""
    return StatementQueryService(get_session_factory())


def get_transaction_category_service() -> TransactionCategoryService:
    """Build the service that applies a person's category corrections."""
    return TransactionCategoryService(get_session_factory())


def get_transaction_query_service() -> TransactionQueryService:
    """Build the transaction read service."""
    return TransactionQueryService(get_session_factory())


StatementIngestionServiceDep = Annotated[
    StatementIngestionService, Depends(get_statement_ingestion_service)
]
StatementQueryServiceDep = Annotated[StatementQueryService, Depends(get_statement_query_service)]
TransactionCategoryServiceDep = Annotated[
    TransactionCategoryService, Depends(get_transaction_category_service)
]
TransactionQueryServiceDep = Annotated[
    TransactionQueryService, Depends(get_transaction_query_service)
]
