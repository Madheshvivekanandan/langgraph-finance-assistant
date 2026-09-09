"""Use case: aggregate stored transactions for the dashboard."""

from sqlalchemy.orm import Session, sessionmaker

from app.domain.category_total import CategoryTotal
from app.domain.month import Month
from app.domain.month_total import MonthTotal
from app.domain.transaction_category import TransactionCategory
from app.repositories.transaction_repository import TransactionRepository


class SummaryService:
    """Serves the rolled-up numbers behind the dashboard."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def monthly_totals(self) -> list[MonthTotal]:
        """Return income and expense per month, newest first."""
        with self._session_factory() as session:
            rows = TransactionRepository(session).monthly_totals()
        return [
            MonthTotal(
                month=Month(year=month_start.year, month=month_start.month),
                income=income,
                expense=expense,
                transaction_count=transaction_count,
            )
            for month_start, income, expense, transaction_count in rows
        ]

    def category_totals(self, *, month: Month | None = None) -> list[CategoryTotal]:
        """Return spending per category, largest first.

        Args:
            month: Restrict to one calendar month, or None for all time.
        """
        with self._session_factory() as session:
            rows = TransactionRepository(session).category_totals(month=month)
        return [
            CategoryTotal(
                category=TransactionCategory(category),
                amount=amount,
                transaction_count=transaction_count,
            )
            for category, amount, transaction_count in rows
        ]
