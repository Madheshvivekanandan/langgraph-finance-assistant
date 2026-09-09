"""Conditional-edge functions for the statement graph.

A router reads state and returns the *name* of the next node. It never mutates
state - that is what keeps the graph's control flow inspectable in Studio.
"""

from typing import Literal

from app.graphs.statement.state import StatementState


def route_after_parse(state: StatementState) -> Literal["normalize_rows", "record_failure"]:
    """Continue to normalization unless parsing recorded an error."""
    return "record_failure" if state.get("error") else "normalize_rows"


def route_after_normalize(
    state: StatementState,
) -> Literal["apply_category_rules", "record_failure"]:
    """Continue to categorization unless normalization recorded an error."""
    return "record_failure" if state.get("error") else "apply_category_rules"


def route_after_rules(
    state: StatementState,
) -> Literal["categorize_with_llm", "store_transactions"]:
    """Skip the model entirely when the keyword rules categorized everything.

    The cheapest LLM call is the one never made, so this is a routing decision
    rather than an early return inside the node - it stays visible in Studio.
    """
    transactions = state.get("transactions", [])
    if any(not transaction.is_categorized for transaction in transactions):
        return "categorize_with_llm"
    return "store_transactions"
