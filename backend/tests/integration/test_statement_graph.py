"""End-to-end tests for the statement ingestion graph against a real database."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.exceptions import DuplicateStatementError
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


def test_graph_creates_the_statement_it_writes_against(
    session_factory: sessionmaker[Session],
) -> None:
    """The graph runs from a CSV alone - no caller-supplied statement row."""
    graph = build_statement_graph(session_factory)

    result = graph.invoke({"raw_csv": _GOOD_CSV, "filename": "july.csv"})

    assert result["stored_count"] == 3
    with session_factory() as session:
        statement = session.get(Statement, result["statement_id"])
        assert statement is not None
        assert statement.filename == "july.csv"
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


def test_graph_defaults_the_filename_when_none_is_given(
    session_factory: sessionmaker[Session],
) -> None:
    """A Studio run supplies only raw_csv, so filename must be optional."""
    graph = build_statement_graph(session_factory)

    result = graph.invoke({"raw_csv": _GOOD_CSV})

    with session_factory() as session:
        statement = session.get(Statement, result["statement_id"])
        assert statement is not None
        assert statement.filename == "statement.csv"


def test_graph_rejects_the_same_content_twice(
    session_factory: sessionmaker[Session],
) -> None:
    graph = build_statement_graph(session_factory)
    graph.invoke({"raw_csv": _GOOD_CSV, "filename": "july.csv"})

    # No statement row exists for a duplicate, so there is nowhere to record the
    # failure: it raises instead of travelling as state.
    with pytest.raises(DuplicateStatementError):
        graph.invoke({"raw_csv": _GOOD_CSV, "filename": "july-again.csv"})


def test_graph_routes_unreadable_header_to_the_failure_path(
    session_factory: sessionmaker[Session],
) -> None:
    graph = build_statement_graph(session_factory)

    result = graph.invoke({"raw_csv": "Foo,Bar\n1,2\n", "filename": "junk.csv"})

    with session_factory() as session:
        statement = session.get(Statement, result["statement_id"])
        assert statement is not None
        assert statement.status == StatementStatus.FAILED.value
        assert "date column" in (statement.error_message or "")
        # The failure path must not have written any transactions.
        assert session.execute(select(Transaction)).first() is None


def test_graph_routes_all_rows_unreadable_to_the_failure_path(
    session_factory: sessionmaker[Session],
) -> None:
    graph = build_statement_graph(session_factory)

    result = graph.invoke(
        {"raw_csv": "Date,Description,Amount\nnot-a-date,X,100\n", "filename": "bad.csv"}
    )

    with session_factory() as session:
        statement = session.get(Statement, result["statement_id"])
        assert statement is not None
        assert statement.status == StatementStatus.FAILED.value
        assert "all 1 data rows were skipped" in (statement.error_message or "")


def test_graph_input_schema_rejects_injected_state(
    session_factory: sessionmaker[Session],
) -> None:
    """A caller must not be able to bypass the parser or hijack a statement row."""
    graph = build_statement_graph(session_factory)

    result = graph.invoke(
        {
            "raw_csv": _GOOD_CSV,
            "filename": "july.csv",
            # Neither key is part of StatementGraphInput, so both must be ignored.
            "transactions": [{"description": "FAKE", "amount": "999999.00"}],
            "statement_id": 4242,
        }
    )

    assert result["statement_id"] != 4242
    with session_factory() as session:
        descriptions = set(session.execute(select(Transaction.description)).scalars())
        assert "FAKE" not in descriptions
        assert len(descriptions) == 3
