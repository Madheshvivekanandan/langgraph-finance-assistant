"""Tool: totals per month, for the chat agent."""

import json

from langchain_core.tools import StructuredTool

from app.services.summary_service import SummaryService


def build_monthly_summary_tool(summary_service: SummaryService) -> StructuredTool:
    """Build the `get_monthly_summary` tool, closing over an injected service.

    A factory rather than a module-level `@tool` function: the service carries a
    `session_factory` that tests point at `myfinance_test`, and a module-level
    singleton could not receive that per-test substitution.
    """

    def get_monthly_summary() -> str:
        """Return total income, spending, and transaction count per month, newest first.

        Covers every month that has data. Call this to answer questions about
        totals over time, to compare months, or to find out which months have
        data at all - including when the user names a month without a year.
        """
        totals = summary_service.monthly_totals()
        return json.dumps(
            [
                {
                    "month": str(total.month),
                    "income": str(total.income),
                    "expense": str(total.expense),
                    "net": str(total.net),
                    "transaction_count": total.transaction_count,
                }
                for total in totals
            ]
        )

    return StructuredTool.from_function(get_monthly_summary)
