"""Graph node: mark the statement AWAITING_REVIEW before the graph suspends."""

import logging

from sqlalchemy.orm import Session, sessionmaker

from app.domain.exceptions import StatementNotFoundError
from app.domain.statement_status import StatementStatus
from app.graphs.statement.state import StatementState
from app.repositories.statement_repository import StatementRepository

logger = logging.getLogger(__name__)


class MarkAwaitingReviewNode:
    """Sets the statement's status before a person is asked to confirm anything.

    This is the only side effect on the pause path, and it runs exactly once
    because it sits *before* `review_low_confidence`'s `interrupt()` in the
    graph: that node re-runs from its first line on every resume, so a
    database write there would repeat. This node does not re-run.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __call__(self, state: StatementState) -> dict[str, object]:
        """Set the statement's status to AWAITING_REVIEW.

        Raises:
            StatementNotFoundError: If the statement row vanished mid-run.
        """
        statement_id = state["statement_id"]
        with self._session_factory() as session, session.begin():
            statement = StatementRepository(session).find_by_id(statement_id)
            if statement is None:
                raise StatementNotFoundError(statement_id)
            statement.status = StatementStatus.AWAITING_REVIEW.value

        logger.info("statement_awaiting_review", extra={"statement_id": statement_id})
        return {}
