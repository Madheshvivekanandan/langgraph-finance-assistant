"""Tool: spending broken down by category, for the chat agent."""

import json

from langchain_core.tools import StructuredTool

from app.domain.exceptions import InvalidMonthError
from app.domain.month import Month
from app.services.summary_service import SummaryService


def build_spending_by_category_tool(summary_service: SummaryService) -> StructuredTool:
    """Build the `get_spending_by_category` tool, closing over an injected service."""

    def get_spending_by_category(month: str | None = None) -> str:
        """Return total spending per category, largest first. Spending only - income is excluded.

        Args:
            month: Restrict to one calendar month, as 'YYYY-MM'. Omit for all time.
        """
        try:
            parsed_month = Month.parse(month) if month else None
        except InvalidMonthError:
            return f"Invalid month {month!r}. Use YYYY-MM."

        totals = summary_service.category_totals(month=parsed_month)
        return json.dumps(
            [
                {
                    "category": total.category.value,
                    "amount": str(total.amount),
                    "transaction_count": total.transaction_count,
                }
                for total in totals
            ]
        )

    return StructuredTool.from_function(get_spending_by_category)
