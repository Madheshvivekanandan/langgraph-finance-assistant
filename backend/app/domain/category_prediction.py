"""A model's guess at one transaction's category."""

from dataclasses import dataclass
from decimal import Decimal

from app.domain.transaction_category import TransactionCategory


@dataclass(frozen=True, slots=True)
class CategoryPrediction:
    """One predicted category and how sure the model was, from 0 to 1."""

    category: TransactionCategory
    confidence: Decimal
