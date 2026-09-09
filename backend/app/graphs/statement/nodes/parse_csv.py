"""Graph node: turn raw CSV text into rows, or explain why it cannot."""

import csv
import io
import logging

from app.domain.exceptions import StatementParseError
from app.graphs.statement.csv_columns import CsvColumns
from app.graphs.statement.state import StatementState

logger = logging.getLogger(__name__)


def parse_csv(state: StatementState) -> dict[str, object]:
    """Read the uploaded text as CSV and confirm the columns we need are present.

    An unreadable file is an *expected* outcome, so it is returned as state
    (`error`) for the router to act on, not raised. Only genuinely unexpected
    faults raise out of a node.
    """
    try:
        reader = csv.DictReader(io.StringIO(state["raw_csv"]))
        headers = list(reader.fieldnames or [])
        CsvColumns.detect(headers)
        rows = [
            {key: (value or "") for key, value in row.items() if key is not None} for row in reader
        ]
    except StatementParseError as exc:
        logger.info("statement_parse_failed", extra={"reason": str(exc)})
        return {"error": str(exc)}
    except csv.Error as exc:
        logger.info("statement_csv_malformed", extra={"reason": str(exc)})
        return {"error": f"the file is not valid CSV: {exc}"}
    except Exception as exc:  # noqa: BLE001 - see below
        # Returned as state rather than raised, so the graph's own failure edge
        # carries it to record_failure. Raising would need a node-level error
        # handler instead, which the runtime dispatches to outside the edge
        # graph - invisible in the diagram. This node has no retry policy, so
        # nothing is lost by handling it here.
        logger.exception("statement_parse_crashed")
        return {"error": f"the file could not be read: {exc}"}

    if not rows:
        return {"error": "the file has a valid header but no data rows"}
    return {"rows": rows}
