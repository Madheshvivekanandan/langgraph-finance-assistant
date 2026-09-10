"""Response schema for a statement's pending review."""

from pydantic import BaseModel

from app.schemas.statement_review_item_out import StatementReviewItemOut


class StatementReviewOut(BaseModel):
    """Everything a statement's paused run is asking a person to confirm."""

    statement_id: int
    filename: str
    threshold: str
    items: list[StatementReviewItemOut]
