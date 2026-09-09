"""Response schema for one category's spending."""

from decimal import Decimal

from pydantic import BaseModel, field_serializer


class CategorySummaryOut(BaseModel):
    """How much was spent in one category."""

    category: str
    label: str
    amount: Decimal
    transaction_count: int

    @field_serializer("amount")
    def serialize_amount(self, amount: Decimal) -> str:
        """Money crosses the wire as a decimal string, never a float."""
        return f"{amount:.2f}"
