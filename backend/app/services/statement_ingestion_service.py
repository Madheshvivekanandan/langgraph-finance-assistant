"""Use case: take an uploaded statement file and turn it into stored transactions."""

import hashlib
import logging

from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.exceptions import DuplicateStatementError, StatementNotFoundError
from app.domain.statement_status import StatementStatus
from app.graphs.statement.state import StatementState
from app.models.statement import Statement
from app.repositories.statement_repository import StatementRepository

logger = logging.getLogger(__name__)


class StatementIngestionService:
    """Creates the statement record, runs the ingestion graph, returns the outcome."""

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
            DuplicateStatementError: If these exact bytes were already ingested.
            StatementNotFoundError: If the record disappeared mid-run.
        """
        file_hash = hashlib.sha256(content).hexdigest()
        raw_csv = self._decode(content)
        statement_id = self._create_statement(filename=filename, file_hash=file_hash)

        # The graph owns the outcome: it writes the transactions and sets the
        # statement's final status, so this service only has to read it back.
        self._graph.invoke({"statement_id": statement_id, "raw_csv": raw_csv})

        with self._session_factory() as session:
            statement = StatementRepository(session).find_by_id(statement_id)
            if statement is None:
                raise StatementNotFoundError(statement_id)
            return statement

    def _create_statement(self, *, filename: str, file_hash: str) -> int:
        """Insert the statement row in PROCESSING and return its id.

        Raises:
            DuplicateStatementError: If the unique file_hash constraint rejects it.
        """
        try:
            with self._session_factory() as session, session.begin():
                statement = StatementRepository(session).add(
                    Statement(
                        filename=filename,
                        file_hash=file_hash,
                        status=StatementStatus.PROCESSING.value,
                    )
                )
                return statement.id
        except IntegrityError as exc:
            # The unique constraint is the real guard: a prior existence check
            # would still lose a race between two simultaneous uploads.
            # Key must not be "filename": that is a reserved LogRecord attribute
            # and logging raises KeyError rather than overwrite it.
            logger.info("duplicate_statement_rejected", extra={"statement_filename": filename})
            raise DuplicateStatementError(filename) from exc

    @staticmethod
    def _decode(content: bytes) -> str:
        """Decode file bytes as text, tolerating a BOM and non-UTF-8 exports."""
        try:
            return content.decode("utf-8-sig")
        except UnicodeDecodeError:
            # Some Indian bank exports are still Windows-1252; never fail on encoding.
            return content.decode("cp1252", errors="replace")
