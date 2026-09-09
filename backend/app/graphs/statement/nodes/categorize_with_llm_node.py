"""Graph node: ask a model about the transactions no rule matched."""

import logging
from dataclasses import replace

from app.domain.categorization_source import CategorizationSource
from app.domain.category_suggester import CategorySuggester
from app.graphs.statement.state import StatementState

logger = logging.getLogger(__name__)


class CategorizeWithLlmNode:
    """Fills in categories the keyword rules could not.

    Best-effort by design. Categorization enriches a statement; it does not
    define one. So this node never fails the run: with no suggester configured,
    or if the provider errors, the affected rows stay UNCATEGORIZED and
    ingestion still completes. That is also why it carries no retry_policy -
    the client does its own retrying, and exhausting it is not fatal here.
    """

    def __init__(self, suggester: CategorySuggester | None) -> None:
        self._suggester = suggester

    def __call__(self, state: StatementState) -> dict[str, object]:
        """Categorize the still-uncategorized transactions, if that is possible."""
        transactions = state["transactions"]
        pending_positions = [
            position
            for position, transaction in enumerate(transactions)
            if not transaction.is_categorized
        ]

        if not pending_positions:
            return {"llm_categorized_count": 0}
        if self._suggester is None:
            logger.info(
                "llm_categorization_skipped",
                extra={"reason": "no OPENAI_API_KEY configured", "pending": len(pending_positions)},
            )
            return {"llm_categorized_count": 0}

        pending = [transactions[position] for position in pending_positions]
        try:
            predictions = self._suggester.suggest(pending)
        except Exception:  # noqa: BLE001 - a provider fault must not fail ingestion
            logger.exception("llm_categorization_failed", extra={"pending": len(pending_positions)})
            return {"llm_categorized_count": 0}

        categorized = list(transactions)
        for pending_index, prediction in predictions.items():
            position = pending_positions[pending_index]
            categorized[position] = replace(
                categorized[position],
                category=prediction.category,
                categorized_by=CategorizationSource.LLM,
                confidence=prediction.confidence,
            )

        logger.info(
            "llm_categorization_applied",
            extra={"categorized": len(predictions), "asked": len(pending)},
        )
        return {"transactions": categorized, "llm_categorized_count": len(predictions)}
