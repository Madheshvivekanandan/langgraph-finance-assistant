"""Public input contract of the statement ingestion graph."""

from typing_extensions import TypedDict


class StatementGraphInput(TypedDict):
    """The only keys a caller may pass into the graph.

    Deliberately narrower than StatementState: without this, a caller could
    inject `transactions` directly and skip the parser entirely.
    """

    statement_id: int
    raw_csv: str
