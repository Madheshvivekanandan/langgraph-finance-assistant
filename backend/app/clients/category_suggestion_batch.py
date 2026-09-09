"""The model's structured reply for a batch of transactions."""

from pydantic import BaseModel, Field

from app.clients.category_suggestion_item import CategorySuggestionItem


class CategorySuggestionBatch(BaseModel):
    """One categorization per transaction sent, keyed by the prompt's index."""

    suggestions: list[CategorySuggestionItem] = Field(
        description="Exactly one entry per transaction in the prompt"
    )
