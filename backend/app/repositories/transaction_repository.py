"""Persistence access for transactions. The only place transaction SQL is written."""

from datetime import date

from sqlalchemy import func, literal, select, tuple_
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


class TransactionRepository:
    """Reads and writes transaction rows.

    Never commits: the caller owns the transaction boundary.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add_all(self, transactions: list[Transaction]) -> None:
        """Stage many transaction rows in one round trip."""
        self._session.add_all(transactions)

    def find_by_id(self, transaction_id: int) -> Transaction | None:
        """Return the transaction with this id, or None."""
        return self._session.get(Transaction, transaction_id)

    def list_page(self, *, limit: int, cursor: tuple[date, int] | None = None) -> list[Transaction]:
        """Return one page, newest first, using keyset pagination.

        The sort is (transaction_date DESC, id DESC) - the id breaks ties so the
        order is total and the cursor can never skip or repeat a row.

        Args:
            limit: Maximum rows to return.
            cursor: The (date, id) of the last row of the previous page.
        """
        query = (
            select(Transaction)
            .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
            .limit(limit)
        )
        if cursor is not None:
            cursor_date, cursor_id = cursor
            # Row-value comparison: strictly "earlier in the sort order than the
            # cursor". Postgres can drive this straight off the composite index.
            query = query.where(
                tuple_(Transaction.transaction_date, Transaction.id)
                < tuple_(literal(cursor_date), literal(cursor_id))
            )
        return list(self._session.execute(query).scalars())

    def count_for_statement(self, statement_id: int) -> int:
        """Return how many transactions belong to a statement."""
        return self._session.execute(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.statement_id == statement_id)
        ).scalar_one()
