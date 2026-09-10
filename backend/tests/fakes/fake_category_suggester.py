"""A deterministic, call-recording stand-in for the OpenAI category suggester.

Exists so the integration suite never makes a live model call. A real suggester
does not just cost money and time: since the review change, its confidence
decides whether the graph pauses and therefore whether any transaction is
stored at all, so a live call makes unrelated tests pass or fail at random.
"""

from decimal import Decimal

from app.domain.category_prediction import CategoryPrediction
from app.domain.parsed_transaction import ParsedTransaction
from app.domain.transaction_category import TransactionCategory


class FakeCategorySuggester:
    """Answers every transaction with the same prediction, and records the asks.

    The default is `OTHER` at full confidence: a category no keyword rule ever
    assigns (so a test can tell rule output from fake output) and a confidence
    above the review threshold (so ingestion runs straight through, as it did
    before the review path existed). Tests that want the review path construct
    one with a confidence below the threshold instead.
    """

    def __init__(
        self,
        category: TransactionCategory = TransactionCategory.OTHER,
        confidence: Decimal = Decimal("1.0"),
    ) -> None:
        self.category = category
        self.confidence = confidence
        self.asked: list[str] = []

    def suggest(self, transactions: list[ParsedTransaction]) -> dict[int, CategoryPrediction]:
        """Return one prediction per transaction, remembering what was asked."""
        self.asked.extend(item.description for item in transactions)
        return {
            index: CategoryPrediction(self.category, self.confidence)
            for index in range(len(transactions))
        }
