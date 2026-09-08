"""Use case: read transactions back out, one page at a time."""

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.models.transaction import Transaction
from app.repositories.transaction_repository import TransactionRepository
from app.services.transaction_cursor import TransactionCursor


@dataclass(frozen=True, slots=True)
class TransactionPage:
    """One page of transactions plus the token that fetches the next one."""

    items: list[Transaction]
    next_token: str | None


class TransactionQueryService:
    """Serves paginated reads of stored transactions."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_page(self, *, page_size: int, page_token: str | None) -> TransactionPage:
        """Return one page of transactions, newest first.

        Args:
            page_size: How many rows to return; already clamped by the caller.
            page_token: Cursor from a previous page, or None for the first page.

        Raises:
            InvalidPageTokenError: If `page_token` is not a cursor this API issued.
        """
        cursor = TransactionCursor.decode(page_token) if page_token else None
        with self._session_factory() as session:
            rows = TransactionRepository(session).list_page(
                limit=page_size,
                cursor=(
                    (cursor.transaction_date, cursor.transaction_id) if cursor is not None else None
                ),
            )

        # A full page means there may be more; a short page means we are done.
        next_token = None
        if len(rows) == page_size:
            last = rows[-1]
            next_token = TransactionCursor(
                transaction_date=last.transaction_date, transaction_id=last.id
            ).encode()
        return TransactionPage(items=rows, next_token=next_token)
