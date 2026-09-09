"""Error handler that records an unexpected node failure on the statement."""

import logging

from sqlalchemy.orm import Session, sessionmaker

from app.graphs.statement.nodes.record_failure_node import RecordFailureNode
from app.graphs.statement.state import StatementState

logger = logging.getLogger(__name__)

_REASON = (
    "ingestion failed unexpectedly while processing this file. "
    "The transactions were not saved - re-upload to try again."
)


class RecordUnexpectedFailureNode:
    """Marks the statement FAILED when a node raises instead of returning.

    Attached as a node's `error_handler`, so it runs only after that node's
    retries are exhausted. Without it an unexpected exception escapes
    `graph.invoke()` and leaves the statement at PROCESSING forever: no
    transactions, no reason recorded, and nothing that will ever revisit it.

    Expected failures still travel as state to `record_failure`. This covers
    only the ones no node anticipated.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._record_failure = RecordFailureNode(session_factory)

    def __call__(self, state: StatementState) -> dict[str, object]:
        """Record the failure, and never raise while doing it."""
        statement_id = state.get("statement_id")
        logger.error("statement_ingestion_crashed", extra={"statement_id": statement_id})
        if statement_id is None:
            # No statement row exists yet, so there is nothing to mark.
            return {"error": _REASON}

        try:
            self._record_failure({**state, "error": _REASON})
        except Exception:  # noqa: BLE001 - the handler is the last line of defence
            # Typically the database itself is unreachable, which is what broke
            # the node in the first place. Nothing can be recorded; say so and
            # leave the statement at PROCESSING rather than raising from here.
            logger.exception("statement_failure_unrecordable", extra={"statement_id": statement_id})
        return {"error": _REASON}
