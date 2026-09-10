"""Unit tests for the statement review confidence threshold."""

from datetime import date
from decimal import Decimal

from app.domain.categorization_source import CategorizationSource
from app.domain.low_confidence_policy import LowConfidencePolicy
from app.domain.parsed_transaction import ParsedTransaction
from app.domain.transaction_category import TransactionCategory
from app.domain.transaction_direction import TransactionDirection

_THRESHOLD = Decimal("0.75")


def _transaction(
    *,
    categorized_by: CategorizationSource = CategorizationSource.LLM,
    confidence: Decimal | None = Decimal("0.50"),
) -> ParsedTransaction:
    return ParsedTransaction(
        transaction_date=date(2026, 7, 1),
        description="X",
        amount=Decimal("1.00"),
        direction=TransactionDirection.DEBIT,
        category=TransactionCategory.DINING,
        categorized_by=categorized_by,
        confidence=confidence,
    )


def test_below_threshold_and_llm_is_low_confidence() -> None:
    policy = LowConfidencePolicy(_THRESHOLD)
    transaction = _transaction(confidence=Decimal("0.42"))

    assert policy.is_low_confidence(transaction) is True


def test_exactly_at_threshold_is_not_low_confidence() -> None:
    """The comparison is strict: a row at the cutoff is confident enough."""
    policy = LowConfidencePolicy(_THRESHOLD)
    transaction = _transaction(confidence=_THRESHOLD)

    assert policy.is_low_confidence(transaction) is False


def test_above_threshold_is_not_low_confidence() -> None:
    policy = LowConfidencePolicy(_THRESHOLD)
    transaction = _transaction(confidence=Decimal("0.90"))

    assert policy.is_low_confidence(transaction) is False


def test_rule_categorized_is_never_low_confidence() -> None:
    """A rule match carries no confidence at all - it must never be flagged."""
    policy = LowConfidencePolicy(_THRESHOLD)
    transaction = _transaction(categorized_by=CategorizationSource.RULE, confidence=None)

    assert policy.is_low_confidence(transaction) is False


def test_uncategorized_with_no_confidence_is_never_low_confidence() -> None:
    """The CI guarantee (D9): with no OPENAI_API_KEY, rows stay UNCATEGORIZED/
    NONE/None. If this case were ever flagged low-confidence, every statement
    ingested in CI would pause against a checkpointer-less graph, where
    `interrupt()` raises instead of suspending - failing the whole suite.
    """
    policy = LowConfidencePolicy(_THRESHOLD)
    transaction = _transaction(categorized_by=CategorizationSource.NONE, confidence=None)

    assert policy.is_low_confidence(transaction) is False


def test_select_returns_only_the_low_confidence_positions() -> None:
    policy = LowConfidencePolicy(_THRESHOLD)
    transactions = [
        _transaction(confidence=Decimal("0.90")),
        _transaction(confidence=Decimal("0.42")),
        _transaction(categorized_by=CategorizationSource.RULE, confidence=None),
    ]

    assert policy.select(transactions) == [1]
