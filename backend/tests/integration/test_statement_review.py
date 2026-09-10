"""End-to-end tests for the human-in-the-loop review pause and resume.

The core proof for this feature: a real `interrupt()` against a real
`PostgresSaver`, asserting zero transactions are stored while paused, then a
real `Command(resume=...)` on the same thread, asserting the corrected
category lands on the same statement rather than a re-ingestion.
"""

from decimal import Decimal
from uuid import uuid4

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.categorization_source import CategorizationSource
from app.domain.category_prediction import CategoryPrediction
from app.domain.parsed_transaction import ParsedTransaction
from app.domain.statement_status import StatementStatus
from app.domain.transaction_category import TransactionCategory
from app.graphs.statement.graph import build_statement_graph
from app.models.statement import Statement
from app.models.transaction import Transaction

_UNMATCHED_CSV = (
    "Date,Description,Amount\n"
    "01/07/2026,UPI-KRISHNASAMY K-ZIONMOTORS,-6000.00\n"
    "02/07/2026,UPI-RAMASAMY R-XYZTRADERS,-1200.00\n"
)


class _LowConfidenceStubSuggester:
    """Every row comes back DINING at 0.30 - below the default 0.75 threshold."""

    def suggest(self, transactions: list[ParsedTransaction]) -> dict[int, CategoryPrediction]:
        return {
            index: CategoryPrediction(TransactionCategory.DINING, Decimal("0.30"))
            for index in range(len(transactions))
        }


def test_low_confidence_pauses_then_resumes_on_the_same_thread(
    session_factory: sessionmaker[Session],
    statement_checkpointer: PostgresSaver,
) -> None:
    graph = build_statement_graph(
        session_factory, _LowConfidenceStubSuggester(), checkpointer=statement_checkpointer
    )
    thread_id = str(uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = graph.invoke({"raw_csv": _UNMATCHED_CSV, "filename": "review.csv"}, config=config)

    assert "__interrupt__" in result
    payload = result["__interrupt__"][0].value
    assert payload["threshold"] == "0.75"
    items = payload["items"]
    assert [item["index"] for item in items] == [0, 1]
    assert items[0]["description"] == "UPI-KRISHNASAMY K-ZIONMOTORS"
    assert items[0]["amount"] == "6000.00"
    assert items[0]["confidence"] == "0.30"

    with session_factory() as session:
        statement = session.get(Statement, payload["statement_id"])
        assert statement is not None
        assert statement.status == StatementStatus.AWAITING_REVIEW.value
        assert statement.thread_id == thread_id
        # Nothing is stored while the run is paused.
        assert (
            session.execute(
                select(Transaction).where(Transaction.statement_id == statement.id)
            ).first()
            is None
        )

    resumed = graph.invoke(
        Command(resume={"decisions": [{"index": 0, "category": "GROCERIES"}]}),
        config=config,
    )

    assert resumed["stored_count"] == 2
    with session_factory() as session:
        statement = session.get(Statement, payload["statement_id"])
        assert statement is not None
        assert statement.status == StatementStatus.COMPLETED.value
        assert statement.transaction_count == 2
        assert statement.period_start is not None
        assert statement.period_end is not None

        rows = list(
            session.execute(select(Transaction).order_by(Transaction.transaction_date)).scalars()
        )
        by_description = {row.description: row for row in rows}

        corrected = by_description["UPI-KRISHNASAMY K-ZIONMOTORS"]
        assert corrected.category == TransactionCategory.GROCERIES.value
        assert corrected.categorized_by == CategorizationSource.USER.value
        assert corrected.confidence is None

        untouched = by_description["UPI-RAMASAMY R-XYZTRADERS"]
        assert untouched.category == TransactionCategory.DINING.value
        assert untouched.categorized_by == CategorizationSource.LLM.value
        assert untouched.confidence == Decimal("0.30")

        # Proves this is the same run, not a second ingestion of the file.
        assert session.execute(select(Statement)).all().__len__() == 1

    snapshot = graph.get_state(config)
    assert snapshot.values["statement_id"] == payload["statement_id"]


def test_no_key_configured_ingests_straight_through_with_no_checkpointer(
    session_factory: sessionmaker[Session],
) -> None:
    """The D9 CI path: no OPENAI_API_KEY means no suggester, so nothing pauses.

    CI runs with no key and therefore no checkpointer either. Without the
    `categorized_by is LLM` gate in `LowConfidencePolicy`, every UNCATEGORIZED
    row here would be flagged and `interrupt()` would raise against this
    checkpointer-less graph, failing every upload in CI.
    """
    graph = build_statement_graph(session_factory, None)

    result = graph.invoke({"raw_csv": _UNMATCHED_CSV, "filename": "no-checkpoint.csv"})

    assert "__interrupt__" not in result
    assert result["stored_count"] == 2
    with session_factory() as session:
        statement = session.get(Statement, result["statement_id"])
        assert statement is not None
        assert statement.status == StatementStatus.COMPLETED.value
