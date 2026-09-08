"""Parse money cells out of a statement CSV into exact Decimals."""

import re
from decimal import Decimal, InvalidOperation

# Currency symbols, thousands separators, and the Dr/Cr suffix some banks append.
_NOISE_PATTERN = re.compile(r"(?:₹|rs\.?|inr|,|\s)", re.IGNORECASE)
_SUFFIX_PATTERN = re.compile(r"(dr|cr)\.?$", re.IGNORECASE)


def parse_amount(raw: str) -> Decimal | None:
    """Return the amount in `raw`, or None if the cell is blank or unreadable.

    Handles "1,234.56", "₹1,234.56", "1234.56 Dr", and "(1,234.56)" for negatives.

    Args:
        raw: An amount cell straight from the CSV.
    """
    candidate = raw.strip()
    if not candidate:
        return None

    is_parenthesised = candidate.startswith("(") and candidate.endswith(")")
    if is_parenthesised:
        candidate = candidate[1:-1]

    candidate = _SUFFIX_PATTERN.sub("", candidate.strip())
    candidate = _NOISE_PATTERN.sub("", candidate)
    if not candidate or candidate in {"-", "."}:
        return None

    try:
        amount = Decimal(candidate)
    except InvalidOperation:
        return None
    return -amount if is_parenthesised else amount
