"""Graph node: persist the parsed transactions and close out the statement."""

import logging

from sqlalchemy.orm import Session, sessionmaker

from app.domain.exceptions import StatementNotFoundError
from app.domain.statement_status import StatementStatus
from app.graphs.statement.state import StatementState
from app.models.transaction import Transaction
from app.repositories.statement_repository import StatementRepository
from app.repositories.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)


class StoreTransactionsNode:
    """Writes transactions and marks the statement COMPLETED, in one transaction.

    A class rather than a function because it carries a dependency: the session
    factory is injected so tests can hand it a throwaway database.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __call__(self, state: StatementState) -> dict[str, object]:
        """Persist the batch and update the statement's summary fields.

        Rows and the status update share one transaction, so a statement is
        never left marked COMPLETED with none of its transactions saved.

        Raises:
            StatementNotFoundError: If the statement row vanished mid-run.
        """
        statement_id = state["statement_id"]
        parsed = state["transactions"]

        with self._session_factory() as session, session.begin():
            statements = StatementRepository(session)
            statement = statements.find_by_id(statement_id)
            if statement is None:
                raise StatementNotFoundError(statement_id)

            TransactionRepository(session).add_all(
                [
                    Transaction(
                        statement_id=statement_id,
                        transaction_date=item.transaction_date,
                        description=item.description,
                        amount=item.amount,
                        direction=item.direction.value,
                    )
                    for item in parsed
                ]
            )
            dates = [item.transaction_date for item in parsed]
            statement.status = StatementStatus.COMPLETED.value
            statement.transaction_count = len(parsed)
            statement.period_start = min(dates)
            statement.period_end = max(dates)

        logger.info(
            "statement_stored",
            extra={"statement_id": statement_id, "stored": len(parsed)},
        )
        return {"stored_count": len(parsed)}
