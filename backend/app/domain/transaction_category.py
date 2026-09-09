"""The category set a transaction can be assigned to."""

from enum import StrEnum


class TransactionCategory(StrEnum):
    """Spending and income categories.

    Held in code rather than a lookup table: the set is small, stable, and
    shared by the rules engine, the LLM prompt, and a database CHECK constraint.
    The trade-off is that adding a category needs a migration - acceptable here,
    and it keeps all three definitions from drifting apart.
    """

    GROCERIES = "GROCERIES"
    DINING = "DINING"
    TRANSPORT = "TRANSPORT"
    HOUSING = "HOUSING"
    UTILITIES = "UTILITIES"
    SHOPPING = "SHOPPING"
    ENTERTAINMENT = "ENTERTAINMENT"
    SUBSCRIPTIONS = "SUBSCRIPTIONS"
    HEALTH = "HEALTH"
    EDUCATION = "EDUCATION"
    INVESTMENTS = "INVESTMENTS"
    TRANSFERS = "TRANSFERS"
    CASH = "CASH"
    FEES = "FEES"
    INCOME = "INCOME"
    OTHER = "OTHER"
    # Distinct from OTHER: nothing has decided yet, rather than "decided it is misc".
    UNCATEGORIZED = "UNCATEGORIZED"

    @classmethod
    def assignable(cls) -> list["TransactionCategory"]:
        """Categories a rule, model, or person may choose - everything but UNCATEGORIZED."""
        return [member for member in cls if member is not cls.UNCATEGORIZED]
