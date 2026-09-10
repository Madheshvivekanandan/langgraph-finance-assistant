"""Domain policy: which categorized transactions need a human to confirm them."""

from decimal import Decimal

from app.domain.categorization_source import CategorizationSource
from app.domain.parsed_transaction import ParsedTransaction


class LowConfidencePolicy:
    """Decides which model-categorized transactions are too unsure to store as-is.

    Framework-free: only stdlib and other domain modules, so it stays importable
    from anywhere without pulling in FastAPI, SQLAlchemy, or LangGraph.
    """

    DEFAULT_THRESHOLD = Decimal("0.75")

    def __init__(self, threshold: Decimal = DEFAULT_THRESHOLD) -> None:
        self._threshold = threshold

    @property
    def threshold(self) -> Decimal:
        """The confidence cutoff below which a row is flagged for review."""
        return self._threshold

    def is_low_confidence(self, transaction: ParsedTransaction) -> bool:
        """True only for a model guess strictly below the threshold.

        Gated on `categorized_by is CategorizationSource.LLM`: a rule match or an
        uncategorized row (confidence None with no key configured) must never
        qualify. Without that gate, every statement ingested with no
        OPENAI_API_KEY configured - which is how CI runs - would flag every row
        and pause against a graph with no checkpointer, where `interrupt()`
        raises instead of suspending.
        """
        if transaction.categorized_by is not CategorizationSource.LLM:
            return False
        return transaction.confidence is None or transaction.confidence < self._threshold

    def select(self, transactions: list[ParsedTransaction]) -> list[int]:
        """Return the positions of transactions that need a person to confirm them."""
        return [
            position
            for position, transaction in enumerate(transactions)
            if self.is_low_confidence(transaction)
        ]
