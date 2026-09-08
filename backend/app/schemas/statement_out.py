"""Response schema for a statement."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class StatementOut(BaseModel):
    """An uploaded statement and the outcome of ingesting it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    status: str
    transaction_count: int
    period_start: date | None = None
    period_end: date | None = None
    error_message: str | None = None
    created_at: datetime
