"""A calendar month, and the half-open date range it covers."""

import re
from dataclasses import dataclass
from datetime import date

from app.domain.exceptions import InvalidMonthError

_MONTH_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")


@dataclass(frozen=True, slots=True)
class Month:
    """One calendar month, as a year and a 1-12 month number.

    Exists so month filtering is expressed once, as a half-open range
    [start, end). A BETWEEN over dates would include the final day's boundary in
    two adjacent months and double-count it.
    """

    year: int
    month: int

    @classmethod
    def parse(cls, raw: str) -> "Month":
        """Parse a 'YYYY-MM' string.

        Raises:
            InvalidMonthError: If the string is not a real year and month.
        """
        matched = _MONTH_PATTERN.match(raw.strip())
        if matched is None:
            raise InvalidMonthError(f"month must look like 'YYYY-MM', got {raw!r}")
        year, month = int(matched.group(1)), int(matched.group(2))
        if not 1 <= month <= 12:
            raise InvalidMonthError(f"month must be between 01 and 12, got {raw!r}")
        return cls(year=year, month=month)

    @property
    def start_date(self) -> date:
        """First day of the month, inclusive."""
        return date(self.year, self.month, 1)

    @property
    def end_date_exclusive(self) -> date:
        """First day of the *next* month - the exclusive upper bound."""
        if self.month == 12:
            return date(self.year + 1, 1, 1)
        return date(self.year, self.month + 1, 1)

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"
