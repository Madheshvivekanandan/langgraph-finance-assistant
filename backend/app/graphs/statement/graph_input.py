"""Public input contract of the statement ingestion graph."""

from typing import NotRequired

from typing_extensions import TypedDict


class StatementGraphInput(TypedDict):
    """The only keys a caller may pass into the graph.

    Deliberately narrower than StatementState: without this, a caller could
    inject `transactions` directly and skip the parser entirely.

    Only the CSV text is required, so the graph runs standalone in LangGraph
    Studio - it creates its own statement record.
    """

    raw_csv: str
    filename: NotRequired[str]
