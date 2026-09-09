"""Unit tests for the keyword category rules."""

import pytest

from app.domain.transaction_category import TransactionCategory
from app.graphs.statement.category_rules import CategoryRules


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("UPI-SWIGGY ORDER-9832", TransactionCategory.DINING),
        ("UPI-BLINKIT GROCERIES", TransactionCategory.GROCERIES),
        ("RENT TRANSFER-LANDLORD", TransactionCategory.HOUSING),
        ("ELECTRICITY BILL TNEB", TransactionCategory.UTILITIES),
        ("NETFLIX SUBSCRIPTION", TransactionCategory.SUBSCRIPTIONS),
        ("AMAZON PURCHASE-ORDER 118", TransactionCategory.SHOPPING),
        ("ATM WITHDRAWAL-ANNA NAGAR", TransactionCategory.CASH),
        ("SALARY CREDIT JULY 2026", TransactionCategory.INCOME),
        ("MUTUAL FUND SIP-AXIS", TransactionCategory.INVESTMENTS),
        ("UPI-PETROL BUNK IOC", TransactionCategory.TRANSPORT),
        ("MOBILE RECHARGE JIO", TransactionCategory.UTILITIES),
    ],
)
def test_match_recognizes_common_merchants(description: str, expected: TransactionCategory) -> None:
    assert CategoryRules.match(description) == expected


def test_match_is_case_insensitive() -> None:
    assert CategoryRules.match("upi-swiggy order") == TransactionCategory.DINING


def test_more_specific_keyword_wins_over_a_later_general_one() -> None:
    # "AURAGOLD" must beat "AUTOPAY": a gold-savings mandate is an investment,
    # not a subscription. Ordering in the rules table is what guarantees it.
    assert (
        CategoryRules.match("UPI-AUTOPAY-AURAGOLD-AURAGOLD5.C") == TransactionCategory.INVESTMENTS
    )


def test_match_returns_none_for_an_unknown_merchant() -> None:
    # Person-to-person UPI has no keyword; this is exactly what the LLM gets.
    assert CategoryRules.match("UPI-KRISHNASAMY K-ZIONMOTORS.MK@") is None


def test_rules_are_configured() -> None:
    assert CategoryRules.rule_count() > 50
