"""Response schema for one month's totals."""

from decimal import Decimal

from pydantic import BaseModel, field_serializer


class MonthSummaryOut(BaseModel):
    """Income, expense, and net for a single month."""

    month: str
    income: Decimal
    expense: Decimal
    net: Decimal
    transaction_count: int

    @field_serializer("income", "expense", "net")
    def serialize_money(self, amount: Decimal) -> str:
        """Money crosses the wire as a decimal string, never a float."""
        return f"{amount:.2f}"
