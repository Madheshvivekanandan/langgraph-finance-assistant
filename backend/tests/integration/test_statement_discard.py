"""Service-level tests for discarding a statement stuck AWAITING_REVIEW.

Reuses the low-confidence stub suggester and real checkpointer from
`test_statement_review_api.py` so a genuine AWAITING_REVIEW row with a live
thread exists without needing OPENAI_API_KEY.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.orm import Session, sessionmaker

from app.domain.category_prediction import CategoryPrediction
from app.domain.exceptions import StatementNotAwaitingReviewError, StatementNotFoundError
from app.domain.parsed_transaction import ParsedTransaction
from app.domain.statement_status import StatementStatus
from app.domain.transaction_category import TransactionCategory
from app.graphs.statement.graph import build_statement_graph
from app.models.statement import Statement
from app.repositories.statement_repository import StatementRepository
from app.services.statement_discard_service import StatementDiscardService

_UNMATCHED_CSV = "Date,Description,Amount\n01/07/2026,UPI-KRISHNASAMY K-ZIONMOTORS,-6000.00\n"


class _LowConfidenceStubSuggester:
    def suggest(self, transactions: list[ParsedTransaction]) -> dict[int, CategoryPrediction]:
        return {
            index: CategoryPrediction(TransactionCategory.DINING, Decimal("0.30"))
            for index in range(len(transactions))
        }


def _pause_for_review(
    session_factory: sessionmaker[Session], statement_checkpointer: PostgresSaver
) -> tuple[int, str]:
    """Run the graph to a genuine AWAITING_REVIEW pause and return its id/thread."""
    graph = build_statement_graph(
        session_factory, _LowConfidenceStubSuggester(), checkpointer=statement_checkpointer
    )
    thread_id = str(uuid4())
    result = graph.invoke(
        {"raw_csv": _UNMATCHED_CSV, "filename": "discard.csv"},
        config={"configurable": {"thread_id": thread_id}},
    )
    assert "__interrupt__" in result
    return result["statement_id"], thread_id


def test_discard_a_paused_statement_deletes_the_row(
    session_factory: sessionmaker[Session], statement_checkpointer: PostgresSaver
) -> None:
    statement_id, _ = _pause_for_review(session_factory, statement_checkpointer)
    service = StatementDiscardService(
        session_factory,
        build_statement_graph(session_factory, checkpointer=statement_checkpointer),
    )

    service.discard(statement_id)

    with session_factory() as session:
        assert StatementRepository(session).find_by_id(statement_id) is None


def test_discard_a_paused_statement_removes_its_checkpoint(
    session_factory: sessionmaker[Session], statement_checkpointer: PostgresSaver
) -> None:
    statement_id, thread_id = _pause_for_review(session_factory, statement_checkpointer)
    service = StatementDiscardService(
        session_factory,
        build_statement_graph(session_factory, checkpointer=statement_checkpointer),
    )

    service.discard(statement_id)

    remaining = list(statement_checkpointer.list({"configurable": {"thread_id": thread_id}}))
    assert remaining == []


def test_discard_a_stranded_statement_with_no_thread_id_discards_cleanly(
    session_factory: sessionmaker[Session], statement_checkpointer: PostgresSaver
) -> None:
    """A row that is AWAITING_REVIEW with thread_id=None is the stranded-row regression case."""
    with session_factory() as session:
        statement = Statement(
            filename="stranded.csv",
            file_hash="stranded-hash",
            status=StatementStatus.AWAITING_REVIEW.value,
            thread_id=None,
        )
        session.add(statement)
        session.commit()
        statement_id = statement.id

    service = StatementDiscardService(
        session_factory,
        build_statement_graph(session_factory, checkpointer=statement_checkpointer),
    )

    service.discard(statement_id)

    with session_factory() as session:
        assert StatementRepository(session).find_by_id(statement_id) is None


def test_discard_unknown_statement_raises_not_found(
    session_factory: sessionmaker[Session], statement_checkpointer: PostgresSaver
) -> None:
    service = StatementDiscardService(
        session_factory,
        build_statement_graph(session_factory, checkpointer=statement_checkpointer),
    )

    with pytest.raises(StatementNotFoundError):
        service.discard(999999)


def test_discard_a_completed_statement_raises_and_leaves_it_in_place(
    session_factory: sessionmaker[Session], statement_checkpointer: PostgresSaver
) -> None:
    with session_factory() as session:
        statement = Statement(
            filename="done.csv",
            file_hash="done-hash",
            status=StatementStatus.COMPLETED.value,
            thread_id=None,
        )
        session.add(statement)
        session.commit()
        statement_id = statement.id

    service = StatementDiscardService(
        session_factory,
        build_statement_graph(session_factory, checkpointer=statement_checkpointer),
    )

    with pytest.raises(StatementNotAwaitingReviewError):
        service.discard(statement_id)

    with session_factory() as session:
        assert StatementRepository(session).find_by_id(statement_id) is not None
