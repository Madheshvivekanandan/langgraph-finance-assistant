"""Spending total for one category."""

from dataclasses import dataclass
from decimal import Decimal

from app.domain.transaction_category import TransactionCategory


@dataclass(frozen=True, slots=True)
class CategoryTotal:
    """How much was spent in one category, and over how many transactions."""

    category: TransactionCategory
    amount: Decimal
    transaction_count: int
