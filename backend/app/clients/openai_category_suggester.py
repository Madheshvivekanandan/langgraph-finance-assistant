"""OpenAI adapter that categorizes transactions the keyword rules could not."""

import logging
from decimal import Decimal

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.clients.category_suggestion_batch import CategorySuggestionBatch
from app.domain.category_prediction import CategoryPrediction
from app.domain.parsed_transaction import ParsedTransaction
from app.domain.transaction_category import TransactionCategory

logger = logging.getLogger(__name__)

# Keeps any single prompt small enough to stay accurate and cheap.
_BATCH_SIZE = 40

_SYSTEM_PROMPT = (
    "You categorize personal bank transactions from Indian bank statements. "
    "Descriptions are terse and contain UPI handles, merchant codes, and reference "
    "numbers. Infer the merchant from those fragments. "
    "Return exactly one entry per numbered transaction, reusing the number given. "
    "Use the direction as evidence: CREDIT is usually INCOME or TRANSFERS. "
    "A person-to-person UPI payment with no merchant is TRANSFERS. "
    "Use OTHER only when nothing else fits, and report low confidence when unsure."
)


class OpenAiCategorySuggester:
    """Calls OpenAI with a schema-constrained response to categorize transactions.

    Implements the CategorySuggester protocol. Batched so one statement costs a
    couple of calls rather than one per row.
    """

    def __init__(self, *, api_key: SecretStr, model: str) -> None:
        self._model = ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=0,
            # The client retries transient API faults itself; the node above
            # degrades gracefully if they are exhausted.
            max_retries=2,
        ).with_structured_output(CategorySuggestionBatch)

    def suggest(self, transactions: list[ParsedTransaction]) -> dict[int, CategoryPrediction]:
        """Categorize every transaction, in batches.

        Args:
            transactions: The rows no keyword rule matched.

        Returns:
            Predictions keyed by each transaction's index in `transactions`.
        """
        predictions: dict[int, CategoryPrediction] = {}
        for start in range(0, len(transactions), _BATCH_SIZE):
            chunk = transactions[start : start + _BATCH_SIZE]
            predictions.update(self._suggest_batch(chunk, offset=start))
        return predictions

    def _suggest_batch(
        self, chunk: list[ParsedTransaction], *, offset: int
    ) -> dict[int, CategoryPrediction]:
        prompt = "\n".join(
            f"{index}. {item.description} | {item.direction.value} | INR {item.amount}"
            for index, item in enumerate(chunk)
        )
        reply = self._model.invoke([("system", _SYSTEM_PROMPT), ("human", prompt)])
        if not isinstance(reply, CategorySuggestionBatch):
            logger.warning("llm_reply_unexpected_shape", extra={"got": type(reply).__name__})
            return {}

        predictions: dict[int, CategoryPrediction] = {}
        for suggestion in reply.suggestions:
            # The model can echo an index outside the batch; drop rather than trust.
            if not 0 <= suggestion.index < len(chunk):
                continue
            if suggestion.category is TransactionCategory.UNCATEGORIZED:
                continue
            predictions[offset + suggestion.index] = CategoryPrediction(
                category=suggestion.category,
                confidence=Decimal(str(round(suggestion.confidence, 2))),
            )
        return predictions
