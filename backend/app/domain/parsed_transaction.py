"""One transaction successfully read out of a statement file."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.transaction_direction import TransactionDirection


@dataclass(frozen=True, slots=True)
class ParsedTransaction:
    """A statement row that survived parsing and normalization.

    Framework-free on purpose: this is what the graph passes between nodes,
    before anything touches the database.

    `amount` is always positive; `direction` carries the sign information.
    """

    transaction_date: date
    description: str
    amount: Decimal
    direction: TransactionDirection
