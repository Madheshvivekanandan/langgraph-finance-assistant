"""Port for whatever suggests categories the keyword rules could not."""

from typing import Protocol

from app.domain.category_prediction import CategoryPrediction
from app.domain.parsed_transaction import ParsedTransaction


class CategorySuggester(Protocol):
    """Suggests categories for transactions no rule matched.

    A Protocol owned by the domain, so the graph depends on this shape rather
    than on OpenAI: tests substitute a fake, and swapping providers touches one
    adapter in `clients/`.
    """

    def suggest(self, transactions: list[ParsedTransaction]) -> dict[int, CategoryPrediction]:
        """Map each transaction's position in the list to a prediction.

        Implementations return only the entries they are confident about;
        a missing index means "no suggestion".
        """
        ...
