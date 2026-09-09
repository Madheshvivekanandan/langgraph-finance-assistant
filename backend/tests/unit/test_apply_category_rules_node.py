"""Unit tests for the rules categorization node."""

from datetime import date
from decimal import Decimal

from app.domain.categorization_source import CategorizationSource
from app.domain.parsed_transaction import ParsedTransaction
from app.domain.transaction_category import TransactionCategory
from app.domain.transaction_direction import TransactionDirection
from app.graphs.statement.nodes.apply_category_rules import apply_category_rules


def _transaction(description: str) -> ParsedTransaction:
    return ParsedTransaction(
        transaction_date=date(2026, 7, 1),
        description=description,
        amount=Decimal("100.00"),
        direction=TransactionDirection.DEBIT,
    )


def test_matching_rows_are_categorized_and_marked_as_rule_sourced() -> None:
    state = {"transactions": [_transaction("UPI-SWIGGY ORDER")]}

    result = apply_category_rules(state)

    categorized = result["transactions"][0]
    assert categorized.category == TransactionCategory.DINING
    assert categorized.categorized_by == CategorizationSource.RULE
    # A rule is deterministic, so it records no confidence score.
    assert categorized.confidence is None
    assert result["rule_categorized_count"] == 1


def test_unmatched_rows_are_left_untouched_for_the_model() -> None:
    state = {"transactions": [_transaction("UPI-KRISHNASAMY K-ZIONMOTORS")]}

    result = apply_category_rules(state)

    untouched = result["transactions"][0]
    assert untouched.category == TransactionCategory.UNCATEGORIZED
    assert untouched.categorized_by == CategorizationSource.NONE
    assert result["rule_categorized_count"] == 0


def test_node_does_not_mutate_the_transactions_it_was_given() -> None:
    original = _transaction("UPI-SWIGGY ORDER")
    state = {"transactions": [original]}

    apply_category_rules(state)

    # Frozen dataclass + replace: the input instance must be unchanged.
    assert original.category == TransactionCategory.UNCATEGORIZED
