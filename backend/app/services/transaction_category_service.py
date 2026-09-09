"""Use case: let a person correct a transaction's category."""

import logging

from sqlalchemy.orm import Session, sessionmaker

from app.domain.categorization_source import CategorizationSource
from app.domain.exceptions import TransactionNotFoundError
from app.domain.transaction_category import TransactionCategory
from app.models.transaction import Transaction
from app.repositories.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)


class TransactionCategoryService:
    """Applies a person's category choice over whatever a rule or model decided."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def set_category(self, *, transaction_id: int, category: TransactionCategory) -> Transaction:
        """Set a transaction's category on a person's authority.

        The stored source becomes USER, which is what stops a later re-run from
        quietly overwriting the correction. Any model confidence is cleared: a
        person's decision is not a probability.

        Args:
            transaction_id: The transaction to recategorize.
            category: The category chosen.

        Raises:
            TransactionNotFoundError: If no such transaction exists.
        """
        with self._session_factory() as session, session.begin():
            transaction = TransactionRepository(session).find_by_id(transaction_id)
            if transaction is None:
                raise TransactionNotFoundError(transaction_id)

            transaction.category = category.value
            transaction.categorized_by = (
                CategorizationSource.NONE.value
                if category is TransactionCategory.UNCATEGORIZED
                else CategorizationSource.USER.value
            )
            transaction.confidence = None

        logger.info(
            "transaction_recategorized",
            extra={"transaction_id": transaction_id, "category": category.value},
        )
        return transaction
