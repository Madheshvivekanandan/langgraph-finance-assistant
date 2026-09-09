"""Response schema for a transaction."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer


class TransactionOut(BaseModel):
    """One stored transaction line."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    statement_id: int
    transaction_date: date
    description: str
    amount: Decimal
    direction: str
    category: str
    categorized_by: str
    confidence: Decimal | None = None

    @field_serializer("amount")
    def serialize_amount(self, amount: Decimal) -> str:
        """Emit money as a decimal string so no client can round-trip it through a float."""
        return f"{amount:.2f}"

    @field_serializer("confidence")
    def serialize_confidence(self, confidence: Decimal | None) -> float | None:
        """Confidence is a probability, not money, so a float is the honest shape."""
        return None if confidence is None else float(confidence)
