"""Unit tests for the LLM categorization node, using a stub suggester."""

from datetime import date
from decimal import Decimal

from app.domain.categorization_source import CategorizationSource
from app.domain.category_prediction import CategoryPrediction
from app.domain.parsed_transaction import ParsedTransaction
from app.domain.transaction_category import TransactionCategory
from app.domain.transaction_direction import TransactionDirection
from app.graphs.statement.nodes.categorize_with_llm_node import CategorizeWithLlmNode


def _transaction(
    description: str, category: TransactionCategory | None = None
) -> ParsedTransaction:
    return ParsedTransaction(
        transaction_date=date(2026, 7, 1),
        description=description,
        amount=Decimal("100.00"),
        direction=TransactionDirection.DEBIT,
        category=category or TransactionCategory.UNCATEGORIZED,
        categorized_by=CategorizationSource.RULE if category else CategorizationSource.NONE,
    )


class _StubSuggester:
    """Records what it was asked and returns canned predictions."""

    def __init__(self, predictions: dict[int, CategoryPrediction]) -> None:
        self._predictions = predictions
        self.asked: list[ParsedTransaction] = []

    def suggest(self, transactions: list[ParsedTransaction]) -> dict[int, CategoryPrediction]:
        self.asked = transactions
        return self._predictions


class _FailingSuggester:
    def suggest(self, transactions: list[ParsedTransaction]) -> dict[int, CategoryPrediction]:
        del transactions  # signature must match the protocol; the input is irrelevant
        raise RuntimeError("provider is down")


def test_predictions_are_applied_with_source_and_confidence() -> None:
    suggester = _StubSuggester(
        {0: CategoryPrediction(TransactionCategory.TRANSFERS, Decimal("0.80"))}
    )
    node = CategorizeWithLlmNode(suggester)

    result = node({"transactions": [_transaction("UPI-SOMEONE")]})

    categorized = result["transactions"][0]
    assert categorized.category == TransactionCategory.TRANSFERS
    assert categorized.categorized_by == CategorizationSource.LLM
    assert categorized.confidence == Decimal("0.80")
    assert result["llm_categorized_count"] == 1


def test_only_uncategorized_rows_are_sent_to_the_model() -> None:
    suggester = _StubSuggester({})
    node = CategorizeWithLlmNode(suggester)

    node(
        {
            "transactions": [
                _transaction("UPI-SWIGGY", TransactionCategory.DINING),
                _transaction("UPI-SOMEONE"),
            ]
        }
    )

    # The rule-matched row must not be paid for a second time.
    assert [item.description for item in suggester.asked] == ["UPI-SOMEONE"]


def test_predictions_map_back_to_the_right_rows() -> None:
    """Index 0 from the model means the first *pending* row, not the first row."""
    suggester = _StubSuggester(
        {0: CategoryPrediction(TransactionCategory.TRANSFERS, Decimal("0.90"))}
    )
    node = CategorizeWithLlmNode(suggester)

    result = node(
        {
            "transactions": [
                _transaction("UPI-SWIGGY", TransactionCategory.DINING),
                _transaction("UPI-SOMEONE"),
            ]
        }
    )

    assert result["transactions"][0].category == TransactionCategory.DINING
    assert result["transactions"][1].category == TransactionCategory.TRANSFERS


def test_node_is_a_no_op_when_no_suggester_is_configured() -> None:
    node = CategorizeWithLlmNode(None)

    result = node({"transactions": [_transaction("UPI-SOMEONE")]})

    # Ingestion must still succeed with no API key configured.
    assert result["llm_categorized_count"] == 0
    assert "transactions" not in result


def test_provider_failure_degrades_instead_of_failing_the_run() -> None:
    node = CategorizeWithLlmNode(_FailingSuggester())

    result = node({"transactions": [_transaction("UPI-SOMEONE")]})

    assert result["llm_categorized_count"] == 0


def test_model_is_not_called_when_rules_categorized_everything() -> None:
    suggester = _StubSuggester({})
    node = CategorizeWithLlmNode(suggester)

    node({"transactions": [_transaction("UPI-SWIGGY", TransactionCategory.DINING)]})

    assert suggester.asked == []
