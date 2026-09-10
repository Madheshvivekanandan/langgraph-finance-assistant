"""Request body for submitting statement review decisions."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.statement_review_decision_in import StatementReviewDecisionIn


class StatementReviewDecisionsIn(BaseModel):
    """A batch of review decisions. Empty approves every pending row as-is."""

    model_config = ConfigDict(extra="forbid")

    decisions: list[StatementReviewDecisionIn] = Field(default_factory=list)
