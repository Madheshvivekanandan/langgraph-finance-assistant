"""Tool: free-text transaction search, for the chat agent."""

import json

from langchain_core.tools import StructuredTool

from app.domain.exceptions import InvalidMonthError
from app.domain.month import Month
from app.domain.transaction_category import TransactionCategory
from app.services.transaction_search_service import TransactionSearchService

_MIN_LIMIT = 1
_MAX_LIMIT = 50
_DEFAULT_LIMIT = 20


def build_search_transactions_tool(search_service: TransactionSearchService) -> StructuredTool:
    """Build the `search_transactions` tool, closing over an injected service."""

    def search_transactions(
        query: str | None = None,
        month: str | None = None,
        category: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> str:
        """Find individual transactions, newest first.

        `query` matches text anywhere in the description, case-insensitively.

        Args:
            query: Free text to search for in the description. Omit to list
                transactions without a text filter.
            month: Restrict to one calendar month, as 'YYYY-MM'. Omit for all time.
            category: Restrict to one category. Omit for all categories.
            limit: Maximum rows to return, 1-50. Out-of-range values are clamped.
        """
        try:
            parsed_month = Month.parse(month) if month else None
        except InvalidMonthError:
            return f"Invalid month {month!r}. Use YYYY-MM."

        parsed_category: TransactionCategory | None = None
        if category:
            try:
                parsed_category = TransactionCategory(category)
            except ValueError:
                valid = ", ".join(member.value for member in TransactionCategory)
                return f"Unknown category {category!r}. Valid categories: {valid}."

        clamped_limit = max(_MIN_LIMIT, min(limit, _MAX_LIMIT))
        transactions = search_service.search(
            text=query, month=parsed_month, category=parsed_category, limit=clamped_limit
        )
        return json.dumps(
            [
                {
                    "transaction_date": transaction.transaction_date.isoformat(),
                    "description": transaction.description,
                    "amount": str(transaction.amount),
                    "direction": transaction.direction,
                    "category": transaction.category,
                }
                for transaction in transactions
            ]
        )

    return StructuredTool.from_function(search_transactions)
