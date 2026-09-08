"""Persistence access for statements. The only place statement SQL is written."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.statement import Statement


class StatementRepository:
    """Reads and writes statement rows.

    Never commits: the caller owns the transaction boundary.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, statement: Statement) -> Statement:
        """Stage a new statement row and flush so its generated id is available."""
        self._session.add(statement)
        self._session.flush()
        return statement

    def find_by_id(self, statement_id: int) -> Statement | None:
        """Return the statement with this id, or None."""
        return self._session.get(Statement, statement_id)

    def find_by_file_hash(self, file_hash: str) -> Statement | None:
        """Return the statement ingested from these exact bytes, or None."""
        return self._session.execute(
            select(Statement).where(Statement.file_hash == file_hash)
        ).scalar_one_or_none()

    def list_recent(self, *, limit: int) -> list[Statement]:
        """Return the most recently uploaded statements, newest first."""
        return list(
            self._session.execute(
                select(Statement).order_by(Statement.id.desc()).limit(limit)
            ).scalars()
        )
