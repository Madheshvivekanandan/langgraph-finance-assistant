"""Use case: read uploaded statements back out."""

from sqlalchemy.orm import Session, sessionmaker

from app.models.statement import Statement
from app.repositories.statement_repository import StatementRepository


class StatementQueryService:
    """Serves reads of statement records."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_recent(self, *, limit: int) -> list[Statement]:
        """Return the most recently uploaded statements, newest first.

        Args:
            limit: Maximum rows to return; already clamped by the caller.
        """
        with self._session_factory() as session:
            return StatementRepository(session).list_recent(limit=limit)
