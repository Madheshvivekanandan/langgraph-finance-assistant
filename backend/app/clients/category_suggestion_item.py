"""One entry of the model's structured reply."""

from pydantic import BaseModel, Field

from app.domain.transaction_category import TransactionCategory


class CategorySuggestionItem(BaseModel):
    """A single categorization the model returned.

    `category` is typed as the enum, so the model is constrained to real
    categories by the schema itself rather than by asking politely in the prompt.
    """

    index: int = Field(description="The transaction number given in the prompt")
    category: TransactionCategory = Field(description="Best-fitting category")
    confidence: float = Field(ge=0.0, le=1.0, description="How sure you are, 0 to 1")
