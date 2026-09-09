"""Response schema for the category breakdown."""

from decimal import Decimal

from pydantic import BaseModel, field_serializer

from app.schemas.category_summary_out import CategorySummaryOut


class CategorySummaryListOut(BaseModel):
    """Spending by category, largest first.

    `total` is served alongside so a client can compute each share without
    re-summing, and without the server and client rounding differently.
    """

    month: str | None = None
    total: Decimal
    items: list[CategorySummaryOut]

    @field_serializer("total")
    def serialize_total(self, amount: Decimal) -> str:
        """Money crosses the wire as a decimal string, never a float."""
        return f"{amount:.2f}"
