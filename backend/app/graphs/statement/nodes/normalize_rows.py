"""Graph node: turn raw CSV rows into typed, validated transactions."""

import logging

from app.domain.exceptions import StatementParseError
from app.domain.parsed_transaction import ParsedTransaction
from app.domain.transaction_direction import TransactionDirection
from app.graphs.statement.csv_columns import CsvColumns
from app.graphs.statement.state import StatementState
from app.utils.amount_parser import parse_amount
from app.utils.date_parser import parse_statement_date

logger = logging.getLogger(__name__)

_MISSING_DESCRIPTION = "(no description)"


def _to_transaction(row: dict[str, str], columns: CsvColumns) -> ParsedTransaction | None:
    """Convert one CSV row, or return None if it is not a usable transaction line.

    Statement exports routinely carry opening-balance lines, subtotals, and
    footers; those come back as None and are counted as skipped rather than
    failing the whole file.
    """
    transaction_date = parse_statement_date(row.get(columns.date_column, ""))
    if transaction_date is None:
        return None

    description = row.get(columns.description_column, "").strip() or _MISSING_DESCRIPTION

    if columns.has_signed_amount and columns.amount_column is not None:
        amount = parse_amount(row.get(columns.amount_column, ""))
        if amount is None or amount == 0:
            return None
        # Convention for single-column exports: negative means money left the account.
        direction = TransactionDirection.DEBIT if amount < 0 else TransactionDirection.CREDIT
        return ParsedTransaction(
            transaction_date=transaction_date,
            description=description,
            amount=abs(amount),
            direction=direction,
        )

    debit = (
        parse_amount(row.get(columns.debit_column, ""))
        if columns.debit_column is not None
        else None
    )
    if debit is not None and debit != 0:
        return ParsedTransaction(
            transaction_date=transaction_date,
            description=description,
            amount=abs(debit),
            direction=TransactionDirection.DEBIT,
        )

    credit = (
        parse_amount(row.get(columns.credit_column, ""))
        if columns.credit_column is not None
        else None
    )
    if credit is not None and credit != 0:
        return ParsedTransaction(
            transaction_date=transaction_date,
            description=description,
            amount=abs(credit),
            direction=TransactionDirection.CREDIT,
        )
    return None


def normalize_rows(state: StatementState) -> dict[str, object]:
    """Convert every parsed row into a ParsedTransaction, skipping unusable lines.

    A file where *nothing* is readable is an expected failure and returns
    `error`; a file where only some rows are unusable succeeds and reports the
    skipped count.
    """
    rows = state["rows"]
    try:
        # Re-derived from the row keys rather than threaded through state, so this
        # node stays independently testable.
        columns = CsvColumns.detect(list(rows[0].keys()))
    except StatementParseError as exc:
        return {"error": str(exc)}

    transactions: list[ParsedTransaction] = []
    try:
        for row in rows:
            parsed = _to_transaction(row, columns)
            if parsed is not None:
                transactions.append(parsed)
    except Exception as exc:  # noqa: BLE001 - kept as state so the edge carries it
        # A malformed cell should never crash the run; the failure edge already
        # exists, so this node reports rather than raises.
        logger.exception("statement_normalize_crashed")
        return {"error": f"a row could not be read: {exc}"}

    skipped_row_count = len(rows) - len(transactions)
    if not transactions:
        return {
            "error": (
                f"no readable transactions: all {len(rows)} data rows were skipped. "
                "Check the date and amount formats."
            ),
            "skipped_row_count": skipped_row_count,
        }

    logger.info(
        "statement_rows_normalized",
        extra={"parsed": len(transactions), "skipped": skipped_row_count},
    )
    return {"transactions": transactions, "skipped_row_count": skipped_row_count}
