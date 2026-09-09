"""Use case: take an uploaded statement file and turn it into stored transactions."""

import logging

from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.orm import Session, sessionmaker

from app.domain.exceptions import StatementNotFoundError
from app.graphs.statement.state import StatementState
from app.models.statement import Statement
from app.repositories.statement_repository import StatementRepository

logger = logging.getLogger(__name__)


class StatementIngestionService:
    """Hands an uploaded file to the ingestion graph and reports the outcome.

    Deliberately thin: the graph owns the whole statement lifecycle, from
    creating the record to setting its final status. This service only adapts
    between HTTP bytes and the graph's text input.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        statement_graph: CompiledStateGraph[StatementState],
    ) -> None:
        self._session_factory = session_factory
        self._graph = statement_graph

    def ingest(self, *, filename: str, content: bytes) -> Statement:
        """Ingest one uploaded statement file.

        Args:
            filename: Original name of the uploaded file, for display only.
            content: Raw bytes of the file.

        Returns:
            The statement record, with its final status set by the graph.

        Raises:
            DuplicateStatementError: If this exact content was already ingested.
            StatementNotFoundError: If the record disappeared mid-run.
        """
        result = self._graph.invoke({"raw_csv": self._decode(content), "filename": filename})
        statement_id = result["statement_id"]

        with self._session_factory() as session:
            statement = StatementRepository(session).find_by_id(statement_id)
            if statement is None:
                raise StatementNotFoundError(statement_id)
            return statement

    @staticmethod
    def _decode(content: bytes) -> str:
        """Decode file bytes as text, tolerating a BOM and non-UTF-8 exports."""
        try:
            return content.decode("utf-8-sig")
        except UnicodeDecodeError:
            # Some Indian bank exports are still Windows-1252; never fail on encoding.
            return content.decode("cp1252", errors="replace")
