"""End-to-end tests for the statement ingestion graph against a real database."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.statement_status import StatementStatus
from app.graphs.statement.graph import build_statement_graph
from app.models.statement import Statement
from app.models.transaction import Transaction

_GOOD_CSV = (
    "Date,Description,Amount\n"
    "01/07/2026,SWIGGY ORDER,-450.00\n"
    "02/07/2026,SALARY JULY,85000.00\n"
    "15/07/2026,ELECTRICITY BILL,-2340.50\n"
)


def _create_statement(factory: sessionmaker[Session], *, file_hash: str) -> int:
    with factory() as session, session.begin():
        statement = Statement(
            filename="july.csv",
            file_hash=file_hash,
            status=StatementStatus.PROCESSING.value,
        )
        session.add(statement)
        session.flush()
        return statement.id


def test_graph_stores_transactions_and_completes_the_statement(
    session_factory: sessionmaker[Session],
) -> None:
    statement_id = _create_statement(session_factory, file_hash="hash-good")
    graph = build_statement_graph(session_factory)

    result = graph.invoke({"statement_id": statement_id, "raw_csv": _GOOD_CSV})

    assert result["stored_count"] == 3
    with session_factory() as session:
        statement = session.get(Statement, statement_id)
        assert statement is not None
        assert statement.status == StatementStatus.COMPLETED.value
        assert statement.transaction_count == 3
        assert statement.period_start == date(2026, 7, 1)
        assert statement.period_end == date(2026, 7, 15)

        rows = list(
            session.execute(select(Transaction).order_by(Transaction.transaction_date)).scalars()
        )
        assert [row.amount for row in rows] == [
            Decimal("450.00"),
            Decimal("85000.00"),
            Decimal("2340.50"),
        ]
        assert [row.direction for row in rows] == ["DEBIT", "CREDIT", "DEBIT"]


def test_graph_routes_unreadable_header_to_the_failure_path(
    session_factory: sessionmaker[Session],
) -> None:
    statement_id = _create_statement(session_factory, file_hash="hash-bad-header")
    graph = build_statement_graph(session_factory)

    graph.invoke({"statement_id": statement_id, "raw_csv": "Foo,Bar\n1,2\n"})

    with session_factory() as session:
        statement = session.get(Statement, statement_id)
        assert statement is not None
        assert statement.status == StatementStatus.FAILED.value
        assert "date column" in (statement.error_message or "")
        # The failure path must not have written any transactions.
        assert session.execute(select(Transaction)).first() is None


def test_graph_routes_all_rows_unreadable_to_the_failure_path(
    session_factory: sessionmaker[Session],
) -> None:
    statement_id = _create_statement(session_factory, file_hash="hash-bad-rows")
    graph = build_statement_graph(session_factory)

    graph.invoke(
        {
            "statement_id": statement_id,
            "raw_csv": "Date,Description,Amount\nnot-a-date,X,100\n",
        }
    )

    with session_factory() as session:
        statement = session.get(Statement, statement_id)
        assert statement is not None
        assert statement.status == StatementStatus.FAILED.value
        assert "all 1 data rows were skipped" in (statement.error_message or "")


def test_graph_input_schema_rejects_injected_transactions(
    session_factory: sessionmaker[Session],
) -> None:
    """A caller must not be able to bypass the parser by supplying transactions."""
    statement_id = _create_statement(session_factory, file_hash="hash-injection")
    graph = build_statement_graph(session_factory)

    graph.invoke(
        {
            "statement_id": statement_id,
            "raw_csv": _GOOD_CSV,
            # Not part of StatementGraphInput, so the graph must ignore it.
            "transactions": [{"description": "FAKE", "amount": "999999.00"}],
        }
    )

    with session_factory() as session:
        descriptions = set(session.execute(select(Transaction.description)).scalars())
        assert "FAKE" not in descriptions
        assert len(descriptions) == 3
