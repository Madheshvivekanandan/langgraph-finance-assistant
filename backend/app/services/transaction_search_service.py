"""Use case: free-text search over stored transactions."""

from sqlalchemy.orm import Session, sessionmaker

from app.domain.month import Month
from app.domain.transaction_category import TransactionCategory
from app.models.transaction import Transaction
from app.repositories.transaction_repository import TransactionRepository


class TransactionSearchService:
    """Serves the chat agent's `search_transactions` tool.

    Shaped like SummaryService: a thin session-scoped wrapper over the
    repository, with no business rules of its own to add.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def search(
        self,
        *,
        text: str | None = None,
        month: Month | None = None,
        category: TransactionCategory | None = None,
        limit: int = 20,
    ) -> list[Transaction]:
        """Find individual transactions, newest first.

        Args:
            text: Matches anywhere in the description, case-insensitively.
            month: Restrict to one calendar month.
            category: Restrict to one category.
            limit: Maximum rows to return.
        """
        with self._session_factory() as session:
            return TransactionRepository(session).search(
                text=text, month=month, category=category, limit=limit
            )
