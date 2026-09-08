"""Work out which CSV columns hold the date, description, and amounts."""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.exceptions import StatementParseError

_WHITESPACE = re.compile(r"\s+")

_DATE_ALIASES = frozenset(
    {"date", "transaction date", "txn date", "tran date", "value date", "posting date"}
)
_DESCRIPTION_ALIASES = frozenset(
    {
        "description",
        "narration",
        "particulars",
        "details",
        "remarks",
        "transaction details",
        "transaction remarks",
    }
)
_AMOUNT_ALIASES = frozenset({"amount", "transaction amount", "amount (inr)", "amt"})
_DEBIT_ALIASES = frozenset(
    {"debit", "debit amount", "withdrawal", "withdrawal amt", "withdrawal amount", "dr"}
)
_CREDIT_ALIASES = frozenset(
    {"credit", "credit amount", "deposit", "deposit amt", "deposit amount", "cr"}
)


def _normalize(header: str) -> str:
    """Reduce a raw header to a comparable form: lowercased, single-spaced, no dots."""
    return _WHITESPACE.sub(" ", header.strip().lower()).replace(".", "")


def _find(headers: Sequence[str], aliases: frozenset[str]) -> str | None:
    """Return the first header matching any alias, in the file's own column order."""
    for header in headers:
        if _normalize(header) in aliases:
            return header
    return None


def _require(headers: Sequence[str], aliases: frozenset[str], field: str) -> str:
    """Return the header for `field`, or explain what the file actually had.

    Raises:
        StatementParseError: If no header matches.
    """
    found = _find(headers, aliases)
    if found is None:
        raise StatementParseError(
            f"could not find a {field} column in the CSV header. "
            f"Found columns: {', '.join(headers) or '(none)'}"
        )
    return found


@dataclass(frozen=True, slots=True)
class CsvColumns:
    """Which column of a statement CSV holds which field.

    Two amount layouts are supported: a single signed `amount` column, or a
    separate debit/credit pair. Exactly one of those is populated.
    """

    date_column: str
    description_column: str
    amount_column: str | None
    debit_column: str | None
    credit_column: str | None

    @property
    def has_signed_amount(self) -> bool:
        """True when amounts come from one signed column rather than a debit/credit pair."""
        return self.amount_column is not None

    @classmethod
    def detect(cls, headers: Sequence[str]) -> "CsvColumns":
        """Map a CSV's headers onto the fields the pipeline needs.

        Args:
            headers: Header cells exactly as they appear in the file.

        Returns:
            The resolved column mapping.

        Raises:
            StatementParseError: If a required column is missing or ambiguous.
        """
        date_column = _require(headers, _DATE_ALIASES, "date")
        description_column = _require(headers, _DESCRIPTION_ALIASES, "description")

        amount_column = _find(headers, _AMOUNT_ALIASES)
        debit_column = _find(headers, _DEBIT_ALIASES)
        credit_column = _find(headers, _CREDIT_ALIASES)
        if amount_column is None and debit_column is None and credit_column is None:
            raise StatementParseError(
                "could not find an amount column, or a debit/credit pair, in the CSV "
                f"header. Found columns: {', '.join(headers) or '(none)'}"
            )

        # A debit/credit pair is more specific than a lone signed column, so it wins
        # when a file happens to carry both.
        if debit_column is not None or credit_column is not None:
            return cls(
                date_column=date_column,
                description_column=description_column,
                amount_column=None,
                debit_column=debit_column,
                credit_column=credit_column,
            )
        return cls(
            date_column=date_column,
            description_column=description_column,
            amount_column=amount_column,
            debit_column=None,
            credit_column=None,
        )
