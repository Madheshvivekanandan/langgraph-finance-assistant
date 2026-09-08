"""Unit tests for money cell parsing."""

from decimal import Decimal

import pytest

from app.utils.amount_parser import parse_amount


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("450.00", Decimal("450.00")),
        ("1,234.56", Decimal("1234.56")),
        ("₹1,234.56", Decimal("1234.56")),
        ("Rs. 1,234.56", Decimal("1234.56")),
        ("  99  ", Decimal("99")),
        ("-450.00", Decimal("-450.00")),
        ("(1,234.56)", Decimal("-1234.56")),
        ("1234.56 Dr", Decimal("1234.56")),
        ("1234.56 Cr", Decimal("1234.56")),
    ],
)
def test_parse_amount_reads_known_formats(raw: str, expected: Decimal) -> None:
    assert parse_amount(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "-", "abc", "N/A"])
def test_parse_amount_returns_none_for_unusable_cells(raw: str) -> None:
    assert parse_amount(raw) is None


def test_parse_amount_keeps_exact_precision() -> None:
    # A float would turn this into 0.1 + 0.2 territory; Decimal must not.
    assert parse_amount("0.10") + parse_amount("0.20") == Decimal("0.30")  # type: ignore[operator]
