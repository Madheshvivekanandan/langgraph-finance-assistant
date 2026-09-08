"""Graph node: record why a statement could not be ingested."""

import logging

from sqlalchemy.orm import Session, sessionmaker

from app.domain.exceptions import StatementNotFoundError
from app.domain.statement_status import StatementStatus
from app.graphs.statement.state import StatementState
from app.repositories.statement_repository import StatementRepository

logger = logging.getLogger(__name__)

_MAX_ERROR_LENGTH = 1000


class RecordFailureNode:
    """Terminal node for the error path: marks the statement FAILED with a reason."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __call__(self, state: StatementState) -> dict[str, object]:
        """Store the failure reason against the statement.

        Raises:
            StatementNotFoundError: If the statement row vanished mid-run.
        """
        statement_id = state["statement_id"]
        reason = state.get("error", "ingestion failed for an unrecorded reason")

        with self._session_factory() as session, session.begin():
            statement = StatementRepository(session).find_by_id(statement_id)
            if statement is None:
                raise StatementNotFoundError(statement_id)
            statement.status = StatementStatus.FAILED.value
            statement.error_message = reason[:_MAX_ERROR_LENGTH]

        logger.warning(
            "statement_ingestion_failed",
            extra={"statement_id": statement_id, "reason": reason},
        )
        return {"stored_count": 0}
