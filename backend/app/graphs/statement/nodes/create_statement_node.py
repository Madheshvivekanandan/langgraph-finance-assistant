"""Graph node: open a statement record for this file."""

import hashlib
import logging

from langchain_core.runnables import RunnableConfig
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.domain.exceptions import DuplicateStatementError
from app.domain.statement_status import StatementStatus
from app.graphs.statement.state import StatementState
from app.models.statement import Statement
from app.repositories.statement_repository import StatementRepository

logger = logging.getLogger(__name__)

_DEFAULT_FILENAME = "statement.csv"


class CreateStatementNode:
    """Inserts the PROCESSING statement row the rest of the pipeline writes against.

    Owning this inside the graph is what makes the graph runnable on its own: a
    Studio run needs only a CSV, with no pre-existing row to point at.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __call__(self, state: StatementState, config: RunnableConfig) -> dict[str, object]:
        """Create the statement record and hand its id to the rest of the graph.

        `config` is injected by LangGraph because it is declared here - reading
        the thread id from it (rather than from state) means a Studio run, which
        mints its own thread id outside this codebase, still gets it persisted.

        Raises:
            DuplicateStatementError: If this exact content was already ingested.
                Raised rather than returned as state because there is no
                statement row yet to record the failure against.
        """
        raw_csv = state["raw_csv"]
        filename = state.get("filename") or _DEFAULT_FILENAME
        file_hash = hashlib.sha256(raw_csv.encode()).hexdigest()
        thread_id = config.get("configurable", {}).get("thread_id")

        try:
            with self._session_factory() as session, session.begin():
                statement = StatementRepository(session).add(
                    Statement(
                        filename=filename,
                        file_hash=file_hash,
                        status=StatementStatus.PROCESSING.value,
                        thread_id=thread_id,
                    )
                )
                statement_id = statement.id
        except IntegrityError as exc:
            # The unique constraint is the real guard: a prior existence check
            # would still lose a race between two simultaneous uploads.
            logger.info("duplicate_statement_rejected", extra={"statement_filename": filename})
            raise DuplicateStatementError(filename) from exc

        logger.info("statement_created", extra={"statement_id": statement_id})
        return {"statement_id": statement_id}
