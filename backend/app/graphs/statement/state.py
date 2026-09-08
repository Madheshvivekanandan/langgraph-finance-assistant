"""Internal working state of the statement ingestion graph."""

from typing_extensions import TypedDict

from app.domain.parsed_transaction import ParsedTransaction


class StatementState(TypedDict, total=False):
    """Everything the statement pipeline reads or writes.

    total=False because each node fills in only its own keys; the graph starts
    with just the two keys declared in StatementGraphInput.
    """

    # Supplied by the caller
    statement_id: int
    raw_csv: str
    # Produced by parse_csv
    rows: list[dict[str, str]]
    # Produced by normalize_rows
    transactions: list[ParsedTransaction]
    skipped_row_count: int
    # Produced by store_transactions
    stored_count: int
    # Set by any node that fails in an expected way; presence routes to record_failure
    error: str
