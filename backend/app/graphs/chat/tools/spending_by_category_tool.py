"""Tool: spending broken down by category, for the chat agent."""

import json
from decimal import Decimal

from langchain_core.tools import StructuredTool

from app.domain.exceptions import InvalidMonthError
from app.domain.month import Month
from app.services.summary_service import SummaryService


def build_spending_by_category_tool(summary_service: SummaryService) -> StructuredTool:
    """Build the `get_spending_by_category` tool, closing over an injected service."""

    def get_spending_by_category(month: str | None = None) -> str:
        """Return spending per category, largest first, plus the total across them.

        Spending only - income is excluded. Use `total` directly for "how much
        did I spend"; never add the category amounts together yourself.

        Args:
            month: Restrict to one calendar month, as 'YYYY-MM'. Omit for all time.
        """
        try:
            parsed_month = Month.parse(month) if month else None
        except InvalidMonthError:
            return f"Invalid month {month!r}. Use YYYY-MM."

        totals = summary_service.category_totals(month=parsed_month)
        # Summed here, in code, for the same reason get_monthly_summary reports
        # an overall figure: a model asked to add the categories would produce a
        # plausible number with no way to tell a right one from a wrong one.
        total_spend = sum((total.amount for total in totals), Decimal("0"))
        return json.dumps(
            {
                "month": str(parsed_month) if parsed_month else None,
                "total": str(total_spend),
                "categories": [
                    {
                        "category": total.category.value,
                        "amount": str(total.amount),
                        "transaction_count": total.transaction_count,
                    }
                    for total in totals
                ],
            }
        )

    return StructuredTool.from_function(get_spending_by_category)
