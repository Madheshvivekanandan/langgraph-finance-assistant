"""ORM entity for a single transaction line."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Transaction(Base):
    """One line item read out of a statement.

    `amount` is exact (Numeric, never float) and always positive; `direction`
    says whether the money left or entered the account.
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    statement_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("statements.id", ondelete="CASCADE"), nullable=False
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"Transaction(id={self.id!r}, date={self.transaction_date!r}, amount={self.amount!r})"
        )
