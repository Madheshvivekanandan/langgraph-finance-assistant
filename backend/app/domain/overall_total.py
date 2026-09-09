"""Income and expense summed across every month that has data."""

from dataclasses import dataclass
from decimal import Decimal

from app.domain.month_total import MonthTotal


@dataclass(frozen=True, slots=True)
class OverallTotal:
    """Totals across all months.

    Exists so "what is my total spend" is answered by a number the tools
    computed, not by a model adding rows together. Arithmetic on money is
    exactly what a language model should never be asked to do: it produces a
    plausible figure with no way to tell a correct one from a wrong one.
    """

    income: Decimal
    expense: Decimal
    transaction_count: int
    month_count: int

    @property
    def net(self) -> Decimal:
        """Income minus expense; negative means more went out than came in."""
        return self.income - self.expense

    @classmethod
    def of(cls, monthly_totals: list[MonthTotal]) -> "OverallTotal":
        """Sum a list of monthly totals.

        Pure: takes the months the caller already fetched rather than querying
        again, so a tool can report both views from one round trip.
        """
        return cls(
            income=sum((total.income for total in monthly_totals), Decimal("0")),
            expense=sum((total.expense for total in monthly_totals), Decimal("0")),
            transaction_count=sum(total.transaction_count for total in monthly_totals),
            month_count=len(monthly_totals),
        )
