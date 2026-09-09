"""One transaction successfully read out of a statement."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.categorization_source import CategorizationSource
from app.domain.transaction_category import TransactionCategory
from app.domain.transaction_direction import TransactionDirection


@dataclass(frozen=True, slots=True)
class ParsedTransaction:
    """A statement row that survived parsing, normalization, and categorization.

    Framework-free on purpose: this is what the graph passes between nodes,
    before anything touches the database.

    `amount` is always positive; `direction` carries the sign information.
    Frozen, so a categorizing node produces a new instance via
    `dataclasses.replace` rather than mutating shared state.
    """

    transaction_date: date
    description: str
    amount: Decimal
    direction: TransactionDirection
    category: TransactionCategory = TransactionCategory.UNCATEGORIZED
    categorized_by: CategorizationSource = CategorizationSource.NONE
    # Only set by the LLM path; a rule or a person is not a probability.
    confidence: Decimal | None = None

    @property
    def is_categorized(self) -> bool:
        """True once something has assigned a real category."""
        return self.category is not TransactionCategory.UNCATEGORIZED
