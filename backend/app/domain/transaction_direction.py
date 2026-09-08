"""Whether money left the account or entered it."""

from enum import StrEnum


class TransactionDirection(StrEnum):
    """Direction of a transaction relative to the account holder."""

    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
