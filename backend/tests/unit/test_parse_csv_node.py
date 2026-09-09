"""Unit tests for the parse_csv graph node."""

import pytest

from app.graphs.statement.csv_columns import CsvColumns
from app.graphs.statement.nodes.parse_csv import parse_csv

_VALID_CSV = "Date,Description,Amount\n01/07/2026,SWIGGY,-450.00\n"


def test_parse_csv_returns_rows_for_a_valid_file() -> None:
    result = parse_csv({"statement_id": 1, "raw_csv": _VALID_CSV})

    assert "error" not in result
    assert result["rows"] == [{"Date": "01/07/2026", "Description": "SWIGGY", "Amount": "-450.00"}]


def test_parse_csv_records_error_for_unrecognized_headers() -> None:
    result = parse_csv({"statement_id": 1, "raw_csv": "Foo,Bar\n1,2\n"})

    # An expected failure travels as state, not as an exception.
    assert "rows" not in result
    assert "date column" in str(result["error"])


def test_parse_csv_records_error_for_header_only_file() -> None:
    result = parse_csv({"statement_id": 1, "raw_csv": "Date,Description,Amount\n"})

    assert "no data rows" in str(result["error"])


def test_parse_csv_records_error_for_empty_file() -> None:
    result = parse_csv({"statement_id": 1, "raw_csv": ""})

    assert "error" in result


def test_parse_csv_fills_missing_trailing_cells() -> None:
    result = parse_csv(
        {"statement_id": 1, "raw_csv": "Date,Description,Amount\n01/07/2026,SWIGGY\n"}
    )

    # A short row must not produce a None value that later nodes trip over.
    assert result["rows"] == [{"Date": "01/07/2026", "Description": "SWIGGY", "Amount": ""}]


def test_an_unexpected_fault_is_reported_as_state_not_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A crash here must travel the same failure edge as a bad header.

    Raising instead would need a node-level error handler, which the runtime
    reaches by exception rather than by edge - and so never appears as a
    connection in the graph.
    """

    def explode(_: object) -> CsvColumns:
        raise RuntimeError("something nobody predicted")

    monkeypatch.setattr(CsvColumns, "detect", explode)

    result = parse_csv({"statement_id": 1, "raw_csv": _VALID_CSV})

    assert "rows" not in result
    assert "could not be read" in str(result["error"])
