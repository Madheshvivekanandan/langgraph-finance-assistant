"""Unit tests for CSV column detection."""

import pytest

from app.domain.exceptions import StatementParseError
from app.graphs.statement.csv_columns import CsvColumns


def test_detect_finds_signed_amount_layout() -> None:
    columns = CsvColumns.detect(["Date", "Description", "Amount"])

    assert columns.has_signed_amount
    assert columns.date_column == "Date"
    assert columns.description_column == "Description"
    assert columns.amount_column == "Amount"


def test_detect_finds_debit_credit_layout() -> None:
    columns = CsvColumns.detect(
        ["Transaction Date", "Narration", "Withdrawal Amount", "Deposit Amount"]
    )

    assert not columns.has_signed_amount
    assert columns.debit_column == "Withdrawal Amount"
    assert columns.credit_column == "Deposit Amount"


def test_detect_matches_headers_case_and_spacing_insensitively() -> None:
    columns = CsvColumns.detect(["  TXN  DATE ", "PARTICULARS", "amt"])

    assert columns.date_column == "  TXN  DATE "
    assert columns.description_column == "PARTICULARS"


def test_detect_prefers_debit_credit_pair_when_both_layouts_present() -> None:
    columns = CsvColumns.detect(["Date", "Narration", "Amount", "Debit", "Credit"])

    assert not columns.has_signed_amount
    assert columns.amount_column is None


def test_detect_without_date_column_raises_and_names_what_was_found() -> None:
    with pytest.raises(StatementParseError, match="date column"):
        CsvColumns.detect(["Description", "Amount"])


def test_detect_without_any_amount_column_raises() -> None:
    with pytest.raises(StatementParseError, match="amount column"):
        CsvColumns.detect(["Date", "Description"])


def test_detect_on_empty_header_raises() -> None:
    with pytest.raises(StatementParseError):
        CsvColumns.detect([])
