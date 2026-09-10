"""Use case: let a person resolve the low-confidence rows a run paused on."""

import logging
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from sqlalchemy.orm import Session, sessionmaker

from app.domain.category_decision import CategoryDecision
from app.domain.exceptions import (
    StatementNotAwaitingReviewError,
    StatementNotFoundError,
    StatementReviewUnavailableError,
)
from app.domain.statement_status import StatementStatus
from app.graphs.statement.state import StatementState
from app.models.statement import Statement
from app.repositories.statement_repository import StatementRepository

logger = logging.getLogger(__name__)


class StatementReviewService:
    """Reads and resolves the pending rows of a statement awaiting review.

    Pending rows are read straight from the LangGraph checkpoint on every
    call, never copied into a database column - so there is exactly one place
    they can drift out of date with the run: nowhere.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        statement_graph: CompiledStateGraph[StatementState],
    ) -> None:
        self._session_factory = session_factory
        self._graph = statement_graph

    def get_pending(self, statement_id: int) -> dict[str, Any]:
        """Return the interrupt payload for a statement awaiting review.

        Raises:
            StatementNotFoundError: If no such statement exists.
            StatementNotAwaitingReviewError: If it is not paused for review.
        """
        statement = self._require_awaiting_review(statement_id)
        return self._read_payload(statement)

    def submit(self, statement_id: int, decisions: list[CategoryDecision]) -> Statement:
        """Apply a person's decisions and resume the run.

        Every index is validated against the pending payload before anything
        touches the run, so an unknown index cannot corrupt a paused run
        partway through. An empty `decisions` list approves every pending row
        as the model suggested it.

        Raises:
            StatementNotFoundError: If no such statement exists.
            StatementNotAwaitingReviewError: If it is not paused for review.
            StatementReviewUnavailableError: If a decision names an index that
                is not actually pending.
        """
        statement = self._require_awaiting_review(statement_id)
        payload = self._read_payload(statement)
        pending_indexes = {item["index"] for item in payload["items"]}
        for decision in decisions:
            if decision.index not in pending_indexes:
                raise StatementReviewUnavailableError(statement_id, decision.index)

        self._graph.invoke(
            Command[Any](
                resume={
                    "decisions": [
                        {"index": decision.index, "category": decision.category.value}
                        for decision in decisions
                    ]
                }
            ),
            config=self._config_for(statement),
        )

        logger.info(
            "statement_review_submitted",
            extra={"statement_id": statement_id, "decisions": len(decisions)},
        )
        with self._session_factory() as session:
            resolved = StatementRepository(session).find_by_id(statement_id)
            if resolved is None:
                raise StatementNotFoundError(statement_id)
            return resolved

    def _require_awaiting_review(self, statement_id: int) -> Statement:
        """Load the statement, or raise if it is not paused for review."""
        with self._session_factory() as session:
            statement = StatementRepository(session).find_by_id(statement_id)
            if statement is None:
                raise StatementNotFoundError(statement_id)
            if (
                statement.status != StatementStatus.AWAITING_REVIEW.value
                or statement.thread_id is None
            ):
                raise StatementNotAwaitingReviewError(statement_id)
            return statement

    def _read_payload(self, statement: Statement) -> dict[str, Any]:
        """Read the interrupt payload out of the checkpoint for this thread.

        `StateSnapshot.interrupts` exists on the installed langgraph (1.2.x);
        the `tasks[*].interrupts` fallback covers older releases where it does
        not, per the same shape documented on `PregelTask`.
        """
        snapshot = self._graph.get_state(self._config_for(statement))
        if snapshot.interrupts:
            # The interrupt payload is JSON built by ReviewLowConfidenceNode; cast
            # here documents that shape rather than trusting an untyped Any.
            return cast(dict[str, Any], snapshot.interrupts[0].value)
        for task in snapshot.tasks:
            if task.interrupts:
                return cast(dict[str, Any], task.interrupts[0].value)
        raise StatementNotAwaitingReviewError(statement.id)

    @staticmethod
    def _config_for(statement: Statement) -> RunnableConfig:
        """Build the checkpoint config this statement's run was invoked with."""
        return {"configurable": {"thread_id": statement.thread_id}}
