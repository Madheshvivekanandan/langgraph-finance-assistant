"""A person's category choice for one pending review row."""

from dataclasses import dataclass

from app.domain.transaction_category import TransactionCategory


@dataclass(frozen=True, slots=True)
class CategoryDecision:
    """One correction made during statement review.

    Kept off `app.api`: `StatementReviewService.submit()` takes this domain type
    rather than the Pydantic request schema, so nothing below the API layer
    imports `app.api` - the route maps the schema to this instead.
    """

    index: int
    category: TransactionCategory
