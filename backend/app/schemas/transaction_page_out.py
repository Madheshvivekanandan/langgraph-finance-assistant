"""Response schema for a page of transactions."""

from pydantic import BaseModel

from app.schemas.transaction_out import TransactionOut


class TransactionPageOut(BaseModel):
    """One page of transactions.

    `next` is omitted entirely on the last page - clients detect the end by its
    absence, never by a short page.
    """

    items: list[TransactionOut]
    next: str | None = None
