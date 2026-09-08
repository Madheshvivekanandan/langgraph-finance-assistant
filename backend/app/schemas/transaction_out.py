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

    @field_serializer("amount")
    def serialize_amount(self, amount: Decimal) -> str:
        """Emit money as a decimal string so no client can round-trip it through a float."""
        return f"{amount:.2f}"
