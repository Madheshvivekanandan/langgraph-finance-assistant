"""Parse the date formats Indian bank statement exports actually use."""

from datetime import date, datetime

# Ordered by how often they appear in real exports. Day-first throughout: Indian
# bank statements use DD/MM/YYYY, and no month-first format is accepted because
# "03/04/2026" would otherwise parse silently into the wrong month.
_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%d-%b-%Y",
    "%d-%b-%y",
    "%d %b %Y",
)


def parse_statement_date(raw: str) -> date | None:
    """Return the date encoded in `raw`, or None if no known format matches.

    Args:
        raw: A date cell straight from the CSV, possibly padded.
    """
    candidate = raw.strip()
    if not candidate:
        return None
    for date_format in _DATE_FORMATS:
        try:
            return datetime.strptime(candidate, date_format).date()
        except ValueError:
            continue
    return None
