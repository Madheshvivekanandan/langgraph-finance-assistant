"""ORM entity for an uploaded statement file."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Identity, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Statement(Base):
    """One uploaded statement file and the outcome of ingesting it."""

    __tablename__ = "statements"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # sha256 of the raw bytes; UNIQUE so the same file cannot be counted twice
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Null until at least one transaction is stored; both are derived from the rows
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Populated only when status is FAILED
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The LangGraph checkpoint thread this run can be resumed against. Null for
    # any run that never paused, or that was never invoked with a config at all.
    thread_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"Statement(id={self.id!r}, filename={self.filename!r}, status={self.status!r})"
