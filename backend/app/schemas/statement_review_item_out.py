"""Response schema for one transaction pending statement review."""

from pydantic import BaseModel


class StatementReviewItemOut(BaseModel):
    """One low-confidence row a person must confirm or correct.

    Amount and confidence stay strings all the way through: the interrupt
    payload already serializes them that way (Decimal is not JSON-serializable
    across a LangGraph checkpoint), and money must never cross the wire as a
    float regardless.
    """

    index: int
    transaction_date: str
    description: str
    amount: str
    direction: str
    suggested_category: str
    confidence: str
