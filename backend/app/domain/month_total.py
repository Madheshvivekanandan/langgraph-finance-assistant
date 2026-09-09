"""Income and expense totals for one calendar month."""

from dataclasses import dataclass
from decimal import Decimal

from app.domain.month import Month


@dataclass(frozen=True, slots=True)
class MonthTotal:
    """What came in and went out over one month.

    `expense` counts every DEBIT, transfers and investments included: money that
    left the account left the account. The category breakdown is where that
    distinction becomes visible.
    """

    month: Month
    income: Decimal
    expense: Decimal
    transaction_count: int

    @property
    def net(self) -> Decimal:
        """Income minus expense; negative means the month spent more than it earned."""
        return self.income - self.expense
