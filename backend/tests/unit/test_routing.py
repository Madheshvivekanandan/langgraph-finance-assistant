"""Unit tests for the statement graph's conditional edges."""

from datetime import date
from decimal import Decimal

from app.domain.parsed_transaction import ParsedTransaction
from app.domain.transaction_category import TransactionCategory
from app.domain.transaction_direction import TransactionDirection
from app.graphs.statement.routing import (
    route_after_normalize,
    route_after_parse,
    route_after_rules,
)


def test_route_after_parse_continues_when_no_error() -> None:
    assert route_after_parse({"rows": []}) == "normalize_rows"


def test_route_after_parse_diverts_to_failure_when_error_present() -> None:
    assert route_after_parse({"error": "bad header"}) == "record_failure"


def test_route_after_normalize_continues_when_no_error() -> None:
    assert route_after_normalize({"transactions": []}) == "apply_category_rules"


def test_route_after_normalize_diverts_to_failure_when_error_present() -> None:
    assert route_after_normalize({"error": "nothing readable"}) == "record_failure"


def test_routers_treat_an_empty_error_string_as_no_error() -> None:
    # Guards against a node returning error="" and silently failing the run.
    assert route_after_parse({"error": ""}) == "normalize_rows"


def _transaction(category: TransactionCategory) -> ParsedTransaction:
    return ParsedTransaction(
        transaction_date=date(2026, 7, 1),
        description="X",
        amount=Decimal("1.00"),
        direction=TransactionDirection.DEBIT,
        category=category,
    )


def test_route_after_rules_skips_the_model_when_everything_matched() -> None:
    state = {"transactions": [_transaction(TransactionCategory.DINING)]}

    assert route_after_rules(state) == "store_transactions"


def test_route_after_rules_calls_the_model_when_something_is_left() -> None:
    state = {
        "transactions": [
            _transaction(TransactionCategory.DINING),
            _transaction(TransactionCategory.UNCATEGORIZED),
        ]
    }

    assert route_after_rules(state) == "categorize_with_llm"
