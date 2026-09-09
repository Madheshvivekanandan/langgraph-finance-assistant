"""Tool: totals per month, for the chat agent."""

import json

from langchain_core.tools import StructuredTool

from app.domain.overall_total import OverallTotal
from app.services.summary_service import SummaryService


def build_monthly_summary_tool(summary_service: SummaryService) -> StructuredTool:
    """Build the `get_monthly_summary` tool, closing over an injected service.

    A factory rather than a module-level `@tool` function: the service carries a
    `session_factory` that tests point at `myfinance_test`, and a module-level
    singleton could not receive that per-test substitution.
    """

    def get_monthly_summary() -> str:
        """Return spending and income per month, plus the all-time total.

        `overall` already sums every month, so use it directly for questions
        about totals with no period named ("what is my total spend"). `months`
        holds the per-month breakdown, newest first, for comparisons and for
        resolving a month named without a year.

        Never add the monthly figures together yourself - `overall` is the
        answer, computed exactly.
        """
        totals = summary_service.monthly_totals()
        overall = OverallTotal.of(totals)
        return json.dumps(
            {
                "overall": {
                    "income": str(overall.income),
                    "expense": str(overall.expense),
                    "net": str(overall.net),
                    "transaction_count": overall.transaction_count,
                    "month_count": overall.month_count,
                },
                "months": [
                    {
                        "month": str(total.month),
                        "income": str(total.income),
                        "expense": str(total.expense),
                        "net": str(total.net),
                        "transaction_count": total.transaction_count,
                    }
                    for total in totals
                ],
            }
        )

    return StructuredTool.from_function(get_monthly_summary)
