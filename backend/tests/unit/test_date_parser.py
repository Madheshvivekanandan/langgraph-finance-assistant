"""Unit tests for statement date parsing."""

from datetime import date

import pytest

from app.utils.date_parser import parse_statement_date


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-07-01", date(2026, 7, 1)),
        ("01/07/2026", date(2026, 7, 1)),
        ("01-07-2026", date(2026, 7, 1)),
        ("01/07/26", date(2026, 7, 1)),
        ("01-Jul-2026", date(2026, 7, 1)),
        ("01 Jul 2026", date(2026, 7, 1)),
        ("  01/07/2026  ", date(2026, 7, 1)),
    ],
)
def test_parse_statement_date_reads_known_formats(raw: str, expected: date) -> None:
    assert parse_statement_date(raw) == expected


def test_parse_statement_date_is_day_first_not_month_first() -> None:
    # 03/04/2026 must be 3 April, never 4 March: Indian statements are DD/MM/YYYY.
    assert parse_statement_date("03/04/2026") == date(2026, 4, 3)


@pytest.mark.parametrize("raw", ["", "   ", "not a date", "31/02/2026", "Opening Balance"])
def test_parse_statement_date_returns_none_for_unusable_cells(raw: str) -> None:
    assert parse_statement_date(raw) is None
