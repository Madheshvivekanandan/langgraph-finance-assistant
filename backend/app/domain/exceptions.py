"""Application exception hierarchy.

Grouped in one module because these are trivial subclasses carrying no behaviour;
every other class in this codebase lives in its own file.

Services raise these; the API layer is the only place that maps them to HTTP.
"""


class AppError(Exception):
    """Base for all application errors."""


class DomainError(AppError):
    """A business rule was violated - the caller's input is semantically wrong."""


class StatementParseError(DomainError):
    """A statement file could not be read as transactions."""


class DuplicateStatementError(DomainError):
    """This exact file has already been ingested."""

    def __init__(self, filename: str) -> None:
        super().__init__(f"statement {filename!r} has already been uploaded")
        self.filename = filename


class StatementNotFoundError(DomainError):
    """No statement exists with the requested id."""

    def __init__(self, statement_id: int) -> None:
        super().__init__(f"statement {statement_id} not found")
        self.statement_id = statement_id


class TransactionNotFoundError(DomainError):
    """No transaction exists with the requested id."""

    def __init__(self, transaction_id: int) -> None:
        super().__init__(f"transaction {transaction_id} not found")
        self.transaction_id = transaction_id


class StatementNotAwaitingReviewError(DomainError):
    """The statement is not currently paused for human review."""

    def __init__(self, statement_id: int) -> None:
        super().__init__(f"statement {statement_id} is not awaiting review")
        self.statement_id = statement_id


class StatementReviewUnavailableError(DomainError):
    """A review decision referenced a row that is not pending review."""

    def __init__(self, statement_id: int, index: int) -> None:
        super().__init__(f"statement {statement_id} has no pending row at index {index}")
        self.statement_id = statement_id
        self.index = index


class InvalidMonthError(DomainError):
    """A month filter was not a usable 'YYYY-MM' value."""


class InvalidPageTokenError(DomainError):
    """A pagination cursor was malformed or expired."""


class ChatUnavailableError(DomainError):
    """The chat agent has no model configured (no OPENAI_API_KEY)."""


class GraphNotFoundError(DomainError):
    """No graph is registered under the requested name."""

    def __init__(self, graph_name: str) -> None:
        super().__init__(f"graph {graph_name!r} not found")
        self.graph_name = graph_name
