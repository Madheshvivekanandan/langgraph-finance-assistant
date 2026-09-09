"""Graph node: categorize what keyword rules can, for free."""

import logging
from dataclasses import replace

from app.domain.categorization_source import CategorizationSource
from app.graphs.statement.category_rules import CategoryRules
from app.graphs.statement.state import StatementState

logger = logging.getLogger(__name__)


def apply_category_rules(state: StatementState) -> dict[str, object]:
    """Assign categories from the keyword rules, leaving the rest untouched.

    Runs before the model so the expensive step only sees what deterministic
    matching could not place. On a typical statement this handles most rows.
    """
    transactions = state["transactions"]

    categorized = []
    matched = 0
    for transaction in transactions:
        category = CategoryRules.match(transaction.description)
        if category is None:
            categorized.append(transaction)
            continue
        categorized.append(
            replace(
                transaction,
                category=category,
                categorized_by=CategorizationSource.RULE,
            )
        )
        matched += 1

    logger.info(
        "category_rules_applied",
        extra={"matched": matched, "unmatched": len(transactions) - matched},
    )
    return {"transactions": categorized, "rule_categorized_count": matched}
