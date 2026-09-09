"""Response schema for the monthly summary list."""

from pydantic import BaseModel

from app.schemas.month_summary_out import MonthSummaryOut


class MonthSummaryListOut(BaseModel):
    """Months newest first, wrapped in an object so it can grow fields."""

    items: list[MonthSummaryOut]
