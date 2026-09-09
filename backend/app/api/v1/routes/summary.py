"""Dashboard aggregate endpoints."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import SummaryServiceDep
from app.domain.month import Month
from app.domain.transaction_category import TransactionCategory
from app.schemas.category_summary_list_out import CategorySummaryListOut
from app.schemas.category_summary_out import CategorySummaryOut
from app.schemas.month_summary_list_out import MonthSummaryListOut
from app.schemas.month_summary_out import MonthSummaryOut

router = APIRouter(prefix="/summary", tags=["summary"])

_MONTH_DESCRIPTION = "Calendar month as YYYY-MM; omit for all time"


def _label(category: TransactionCategory) -> str:
    """Turn GROCERIES into Groceries for display."""
    return category.value.replace("_", " ").title()


@router.get(
    "/months",
    response_model=MonthSummaryListOut,
    summary="Income, expense, and net per month",
    description=(
        "Newest first. `expense` counts every debit, transfers and investments "
        "included - money that left the account left the account. Use the "
        "category breakdown to see that split."
    ),
)
def list_monthly_summary(service: SummaryServiceDep) -> MonthSummaryListOut:
    """Return every month that has transactions.

    Not paginated: this grows by one row per month, so the whole series is what
    the trend chart needs anyway.
    """
    return MonthSummaryListOut(
        items=[
            MonthSummaryOut(
                month=str(total.month),
                income=total.income,
                expense=total.expense,
                net=total.net,
                transaction_count=total.transaction_count,
            )
            for total in service.monthly_totals()
        ]
    )


@router.get(
    "/categories",
    response_model=CategorySummaryListOut,
    summary="Spending by category",
    description=(
        "Largest first, debits only - a breakdown of where money went should not "
        "have income mixed into it."
    ),
)
def list_category_summary(
    service: SummaryServiceDep,
    month: Annotated[str | None, Query(description=_MONTH_DESCRIPTION)] = None,
) -> CategorySummaryListOut:
    """Return spending per category for a month, or for all time.

    Raises:
        InvalidMonthError: If `month` is not a usable YYYY-MM value.
    """
    parsed_month = Month.parse(month) if month else None
    totals = service.category_totals(month=parsed_month)
    return CategorySummaryListOut(
        month=str(parsed_month) if parsed_month else None,
        total=sum((total.amount for total in totals), Decimal("0")),
        items=[
            CategorySummaryOut(
                category=total.category.value,
                label=_label(total.category),
                amount=total.amount,
                transaction_count=total.transaction_count,
            )
            for total in totals
        ],
    )
