"""Persistence access for transactions. The only place transaction SQL is written."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Select, cast, func, literal, select, tuple_
from sqlalchemy.orm import Session

from app.domain.month import Month
from app.domain.transaction_category import TransactionCategory
from app.models.transaction import Transaction

_LIKE_ESCAPE_CHAR = "\\"


def _escape_like(text_: str) -> str:
    """Neutralise ILIKE wildcards so a user's search text matches literally.

    Escapes the escape character itself first, then the two ILIKE wildcards -
    otherwise a literal `%` or `_` in a description would silently act as a
    wildcard instead of matching itself.
    """
    return (
        text_.replace(_LIKE_ESCAPE_CHAR, _LIKE_ESCAPE_CHAR * 2)
        .replace("%", f"{_LIKE_ESCAPE_CHAR}%")
        .replace("_", f"{_LIKE_ESCAPE_CHAR}_")
    )


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

    @staticmethod
    def _apply_filters(
        query: Select[tuple[Transaction]],
        *,
        month: Month | None,
        category: TransactionCategory | None,
    ) -> Select[tuple[Transaction]]:
        """Narrow a transaction query by the allowlisted filters."""
        if month is not None:
            # Half-open range: never BETWEEN, which would double-count the boundary.
            query = query.where(
                Transaction.transaction_date >= month.start_date,
                Transaction.transaction_date < month.end_date_exclusive,
            )
        if category is not None:
            query = query.where(Transaction.category == category.value)
        return query

    def list_page(
        self,
        *,
        limit: int,
        cursor: tuple[date, int] | None = None,
        month: Month | None = None,
        category: TransactionCategory | None = None,
    ) -> list[Transaction]:
        """Return one page, newest first, using keyset pagination.

        The sort is (transaction_date DESC, id DESC) - the id breaks ties so the
        order is total and the cursor can never skip or repeat a row.

        Args:
            limit: Maximum rows to return.
            cursor: The (date, id) of the last row of the previous page.
            month: Restrict to one calendar month.
            category: Restrict to one category.
        """
        query = (
            self._apply_filters(select(Transaction), month=month, category=category)
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

    def search(
        self,
        *,
        text: str | None = None,
        month: Month | None = None,
        category: TransactionCategory | None = None,
        limit: int = 20,
    ) -> list[Transaction]:
        """Find individual transactions, newest first.

        For the chat agent's `search_transactions` tool - free text over
        `description` only, since `Transaction` has no separate merchant column.

        Args:
            text: Matches anywhere in the description, case-insensitively.
                None or empty skips the text filter entirely.
            month: Restrict to one calendar month.
            category: Restrict to one category.
            limit: Maximum rows to return; already clamped by the caller.
        """
        query = self._apply_filters(select(Transaction), month=month, category=category)
        if text:
            query = query.where(
                Transaction.description.ilike(f"%{_escape_like(text)}%", escape=_LIKE_ESCAPE_CHAR)
            )
        query = query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).limit(
            limit
        )
        return list(self._session.execute(query).scalars())

    def count_for_statement(self, statement_id: int) -> int:
        """Return how many transactions belong to a statement."""
        return self._session.execute(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.statement_id == statement_id)
        ).scalar_one()

    def monthly_totals(self) -> list[tuple[date, Decimal, Decimal, int]]:
        """Return (month_start, income, expense, count) per month, newest first.

        One grouped query rather than one query per month: the dashboard needs
        every month at once for its trend line.
        """
        month_start = cast(func.date_trunc("month", Transaction.transaction_date), Date)
        query = (
            select(
                month_start.label("month_start"),
                func.coalesce(
                    func.sum(Transaction.amount).filter(Transaction.direction == "CREDIT"),
                    0,
                ).label("income"),
                func.coalesce(
                    func.sum(Transaction.amount).filter(Transaction.direction == "DEBIT"),
                    0,
                ).label("expense"),
                func.count().label("transaction_count"),
            )
            .group_by(month_start)
            .order_by(month_start.desc())
        )
        return [
            (row.month_start, row.income, row.expense, row.transaction_count)
            for row in self._session.execute(query)
        ]

    def category_totals(self, *, month: Month | None = None) -> list[tuple[str, Decimal, int]]:
        """Return (category, amount, count) for spending, largest first.

        DEBIT only: a breakdown of where money went should not have income mixed
        into it.

        Args:
            month: Restrict to one calendar month, or None for all time.
        """
        total = func.sum(Transaction.amount)
        query = (
            select(
                Transaction.category,
                total.label("amount"),
                # Not "count": Row inherits tuple.count, and the label would shadow it.
                func.count().label("transaction_count"),
            )
            .where(Transaction.direction == "DEBIT")
            .group_by(Transaction.category)
            .order_by(total.desc())
        )
        if month is not None:
            query = query.where(
                Transaction.transaction_date >= month.start_date,
                Transaction.transaction_date < month.end_date_exclusive,
            )
        return [
            (row.category, row.amount, row.transaction_count)
            for row in self._session.execute(query)
        ]
