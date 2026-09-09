"""Unit tests for the chat agent's tools, against stubbed services.

Query correctness (half-open months, ILIKE escaping, ordering) is already
covered where the SQL lives: tests/integration/test_transaction_search.py and
tests/integration/test_summary_api.py. These tests cover only what the tool
wrapper itself is responsible for: JSON-encoding money as strings, degrading
gracefully on bad model input instead of raising, and clamping `limit`.
"""

import json
from datetime import date
from decimal import Decimal

from app.domain.category_total import CategoryTotal
from app.domain.month import Month
from app.domain.month_total import MonthTotal
from app.domain.transaction_category import TransactionCategory
from app.graphs.chat.tools.monthly_summary_tool import build_monthly_summary_tool
from app.graphs.chat.tools.search_transactions_tool import build_search_transactions_tool
from app.graphs.chat.tools.spending_by_category_tool import build_spending_by_category_tool
from app.models.transaction import Transaction


class _StubSummaryService:
    """Records what it was asked and returns canned totals."""

    def __init__(
        self,
        *,
        month_totals: list[MonthTotal] | None = None,
        category_totals: list[CategoryTotal] | None = None,
    ) -> None:
        self._month_totals = month_totals or []
        self._category_totals = category_totals or []
        self.category_totals_calls: list[Month | None] = []

    def monthly_totals(self) -> list[MonthTotal]:
        return self._month_totals

    def category_totals(self, *, month: Month | None = None) -> list[CategoryTotal]:
        self.category_totals_calls.append(month)
        return self._category_totals


class _StubSearchService:
    """Records the exact kwargs it was called with."""

    def __init__(self, transactions: list[Transaction] | None = None) -> None:
        self._transactions = transactions or []
        self.calls: list[dict[str, object]] = []

    def search(
        self,
        *,
        text: str | None = None,
        month: Month | None = None,
        category: TransactionCategory | None = None,
        limit: int = 20,
    ) -> list[Transaction]:
        self.calls.append({"text": text, "month": month, "category": category, "limit": limit})
        return self._transactions


def _transaction(**overrides: object) -> Transaction:
    defaults: dict[str, object] = {
        "id": 1,
        "statement_id": 1,
        "transaction_date": date(2026, 7, 1),
        "description": "UPI-SWIGGY ORDER",
        "amount": Decimal("450.00"),
        "direction": "DEBIT",
        "category": "DINING",
    }
    defaults.update(overrides)
    return Transaction(**defaults)  # type: ignore[arg-type]


def test_monthly_summary_serializes_money_as_strings_never_floats() -> None:
    service = _StubSummaryService(
        month_totals=[
            MonthTotal(
                month=Month(year=2026, month=7),
                income=Decimal("85000.00"),
                expense=Decimal("486.00"),
                transaction_count=2,
            )
        ]
    )
    tool = build_monthly_summary_tool(service)

    result = json.loads(tool.invoke({}))

    assert result == [
        {
            "month": "2026-07",
            "income": "85000.00",
            "expense": "486.00",
            "net": "84514.00",
            "transaction_count": 2,
        }
    ]
    assert isinstance(result[0]["income"], str)


def test_spending_by_category_parses_a_valid_month() -> None:
    service = _StubSummaryService(
        category_totals=[
            CategoryTotal(
                category=TransactionCategory.DINING, amount=Decimal("450.00"), transaction_count=1
            )
        ]
    )
    tool = build_spending_by_category_tool(service)

    result = json.loads(tool.invoke({"month": "2026-07"}))

    assert service.category_totals_calls == [Month(year=2026, month=7)]
    assert result == [{"category": "DINING", "amount": "450.00", "transaction_count": 1}]


def test_spending_by_category_reports_an_invalid_month_instead_of_raising() -> None:
    service = _StubSummaryService()
    tool = build_spending_by_category_tool(service)

    result = tool.invoke({"month": "julyy"})

    assert "Invalid month" in result
    assert "julyy" in result
    # A bad month must never reach the service.
    assert service.category_totals_calls == []


def test_search_transactions_serializes_money_as_a_string() -> None:
    service = _StubSearchService(transactions=[_transaction(amount=Decimal("450.50"))])
    tool = build_search_transactions_tool(service)

    result = json.loads(tool.invoke({"query": "swiggy"}))

    assert result[0]["amount"] == "450.50"
    assert isinstance(result[0]["amount"], str)


def test_search_transactions_rejects_an_unknown_category_without_raising() -> None:
    service = _StubSearchService()
    tool = build_search_transactions_tool(service)

    result = tool.invoke({"category": "NONSENSE"})

    assert "Unknown category" in result
    assert "NONSENSE" in result
    assert "DINING" in result  # the valid-categories list is present
    assert service.calls == []


def test_search_transactions_reports_an_invalid_month_instead_of_raising() -> None:
    service = _StubSearchService()
    tool = build_search_transactions_tool(service)

    result = tool.invoke({"month": "not-a-month"})

    assert "Invalid month" in result
    assert service.calls == []


def test_search_transactions_clamps_limit_above_the_maximum() -> None:
    service = _StubSearchService()
    tool = build_search_transactions_tool(service)

    tool.invoke({"limit": 500})

    assert service.calls[0]["limit"] == 50


def test_search_transactions_clamps_limit_below_the_minimum() -> None:
    service = _StubSearchService()
    tool = build_search_transactions_tool(service)

    tool.invoke({"limit": 0})

    assert service.calls[0]["limit"] == 1


def test_search_transactions_passes_through_a_valid_category() -> None:
    service = _StubSearchService()
    tool = build_search_transactions_tool(service)

    tool.invoke({"category": "DINING"})

    assert service.calls[0]["category"] == TransactionCategory.DINING
