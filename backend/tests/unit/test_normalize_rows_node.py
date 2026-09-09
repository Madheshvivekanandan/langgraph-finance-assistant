"""Unit tests for the normalize_rows graph node."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.parsed_transaction import ParsedTransaction
from app.domain.transaction_direction import TransactionDirection
from app.graphs.statement.nodes import normalize_rows as normalize_module
from app.graphs.statement.nodes.normalize_rows import normalize_rows


def test_normalize_rows_reads_signed_amounts_into_directions() -> None:
    rows = [
        {"Date": "01/07/2026", "Description": "SWIGGY", "Amount": "-450.00"},
        {"Date": "02/07/2026", "Description": "SALARY", "Amount": "85000.00"},
    ]

    result = normalize_rows({"statement_id": 1, "rows": rows})

    assert result["transactions"] == [
        ParsedTransaction(
            transaction_date=date(2026, 7, 1),
            description="SWIGGY",
            amount=Decimal("450.00"),
            direction=TransactionDirection.DEBIT,
        ),
        ParsedTransaction(
            transaction_date=date(2026, 7, 2),
            description="SALARY",
            amount=Decimal("85000.00"),
            direction=TransactionDirection.CREDIT,
        ),
    ]
    assert result["skipped_row_count"] == 0


def test_normalize_rows_reads_debit_credit_pair_layout() -> None:
    rows = [
        {"Date": "01/07/2026", "Narration": "UPI-SWIGGY", "Debit": "450.00", "Credit": ""},
        {"Date": "05/07/2026", "Narration": "SALARY", "Debit": "", "Credit": "85000.00"},
    ]

    transactions = normalize_rows({"statement_id": 1, "rows": rows})["transactions"]

    assert [item.direction for item in transactions] == [
        TransactionDirection.DEBIT,
        TransactionDirection.CREDIT,
    ]
    assert [item.amount for item in transactions] == [
        Decimal("450.00"),
        Decimal("85000.00"),
    ]


def test_normalize_rows_skips_unusable_lines_but_keeps_the_rest() -> None:
    rows = [
        {"Date": "Opening Balance", "Description": "", "Amount": ""},
        {"Date": "01/07/2026", "Description": "SWIGGY", "Amount": "-450.00"},
        {"Date": "01/07/2026", "Description": "ZERO ROW", "Amount": "0.00"},
    ]

    result = normalize_rows({"statement_id": 1, "rows": rows})

    assert len(result["transactions"]) == 1
    assert result["skipped_row_count"] == 2


def test_normalize_rows_substitutes_a_placeholder_for_a_blank_description() -> None:
    rows = [{"Date": "01/07/2026", "Description": "  ", "Amount": "-450.00"}]

    transactions = normalize_rows({"statement_id": 1, "rows": rows})["transactions"]

    assert transactions[0].description == "(no description)"


def test_normalize_rows_records_error_when_every_row_is_unusable() -> None:
    rows = [
        {"Date": "not a date", "Description": "X", "Amount": "100"},
        {"Date": "also not", "Description": "Y", "Amount": "200"},
    ]

    result = normalize_rows({"statement_id": 1, "rows": rows})

    assert "transactions" not in result
    assert "all 2 data rows were skipped" in str(result["error"])


def test_an_unexpected_fault_is_reported_as_state_not_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed cell must not crash the run; the failure edge carries it."""

    def explode(*_: object) -> None:
        raise RuntimeError("something nobody predicted")

    monkeypatch.setattr(normalize_module, "_to_transaction", explode)

    result = normalize_rows(
        {"statement_id": 1, "rows": [{"Date": "01/07/2026", "Description": "X", "Amount": "-1.00"}]}
    )

    assert "transactions" not in result
    assert "could not be read" in str(result["error"])
