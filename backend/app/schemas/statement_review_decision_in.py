"""Request body for one corrected row during statement review."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.transaction_category import TransactionCategory


class StatementReviewDecisionIn(BaseModel):
    """A person's chosen category for one pending review row.

    `UNCATEGORIZED` is rejected: reviewing a low-confidence guess means picking
    a real category, not deferring the decision again.
    """

    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    category: TransactionCategory

    @field_validator("category")
    @classmethod
    def _reject_uncategorized(cls, value: TransactionCategory) -> TransactionCategory:
        if value is TransactionCategory.UNCATEGORIZED:
            raise ValueError("category must not be UNCATEGORIZED")
        return value
