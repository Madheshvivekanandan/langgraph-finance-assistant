"""Use case: permanently abandon a statement stuck AWAITING_REVIEW."""

import logging

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.orm import Session, sessionmaker

from app.domain.exceptions import StatementNotAwaitingReviewError, StatementNotFoundError
from app.domain.statement_status import StatementStatus
from app.graphs.statement.state import StatementState
from app.repositories.statement_repository import StatementRepository

logger = logging.getLogger(__name__)


class StatementDiscardService:
    """Deletes a statement row that is paused AWAITING_REVIEW and nobody wants to finish.

    Deliberately violates `StatementReviewService`'s invariant that a pending row
    always has a live checkpoint: a discard must also work on a statement whose
    `thread_id` is null or whose thread has no checkpoint rows at all - exactly
    the row this feature exists to unstick. So the guard here checks status
    only, never `thread_id is not None`.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        statement_graph: CompiledStateGraph[StatementState],
    ) -> None:
        self._session_factory = session_factory
        self._graph = statement_graph

    def discard(self, statement_id: int) -> None:
        """Delete a statement paused for review, freeing its `file_hash`.

        Best-effort checkpoint cleanup happens first, so a concurrent
        `POST .../review` cannot resume a run whose statement is about to
        disappear. The row delete itself is not best-effort: if it fails, the
        exception propagates, because the user-visible outcome did not happen.

        Raises:
            StatementNotFoundError: If no such statement exists.
            StatementNotAwaitingReviewError: If it is not paused for review.
        """
        with self._session_factory() as session:
            repository = StatementRepository(session)
            statement = repository.find_by_id(statement_id)
            if statement is None:
                raise StatementNotFoundError(statement_id)
            if statement.status != StatementStatus.AWAITING_REVIEW.value:
                raise StatementNotAwaitingReviewError(statement_id)

            thread_id = statement.thread_id
            if thread_id is not None:
                self._delete_thread(statement_id, thread_id)

            repository.delete(statement)
            session.commit()

        logger.info(
            "statement_discarded", extra={"statement_id": statement_id, "thread_id": thread_id}
        )

    def _delete_thread(self, statement_id: int, thread_id: str) -> None:
        """Erase this thread's checkpoint rows, tolerating any failure.

        The checkpointer and the statements table are different connections,
        so a shared transaction is impossible regardless - failing the whole
        discard because garbage collection failed would leave the person stuck
        in exactly the state this feature exists to escape.
        """
        checkpointer = self._graph.checkpointer
        if not isinstance(checkpointer, BaseCheckpointSaver):
            return
        try:
            checkpointer.delete_thread(thread_id)
        except Exception:
            logger.warning(
                "statement_discard_checkpoint_cleanup_failed",
                extra={"statement_id": statement_id, "thread_id": thread_id},
                exc_info=True,
            )
