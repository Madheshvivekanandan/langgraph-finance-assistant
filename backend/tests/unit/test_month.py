"""Unit tests for the Month value object."""

from datetime import date

import pytest

from app.domain.exceptions import InvalidMonthError
from app.domain.month import Month


def test_parse_reads_a_year_and_month() -> None:
    assert Month.parse("2026-07") == Month(year=2026, month=7)


def test_parse_tolerates_surrounding_whitespace() -> None:
    assert Month.parse("  2026-07  ") == Month(year=2026, month=7)


@pytest.mark.parametrize("raw", ["2026-7", "2026", "26-07", "2026-13", "2026-00", "july", ""])
def test_parse_rejects_anything_else(raw: str) -> None:
    with pytest.raises(InvalidMonthError):
        Month.parse(raw)


def test_range_is_half_open() -> None:
    july = Month(year=2026, month=7)

    assert july.start_date == date(2026, 7, 1)
    # Exclusive upper bound: 1 August is *not* part of July, so adjacent months
    # can never both claim the same day.
    assert july.end_date_exclusive == date(2026, 8, 1)


def test_december_rolls_into_the_next_year() -> None:
    december = Month(year=2026, month=12)

    assert december.end_date_exclusive == date(2027, 1, 1)


def test_str_is_the_wire_format() -> None:
    assert str(Month(year=2026, month=7)) == "2026-07"
    assert str(Month(year=2026, month=12)) == "2026-12"
