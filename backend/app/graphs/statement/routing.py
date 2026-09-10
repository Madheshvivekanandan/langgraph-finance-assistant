"""Conditional-edge functions for the statement graph.

A router reads state and returns the *name* of the next node. It never mutates
state - that is what keeps the graph's control flow inspectable in Studio.
"""

from typing import Literal

from app.domain.low_confidence_policy import LowConfidencePolicy
from app.graphs.statement.state import StatementState

# Module-level singleton rather than a call in the default argument (ruff B008),
# and stateless enough to share safely as a mutable-default-style default.
_DEFAULT_POLICY = LowConfidencePolicy()


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


def route_after_llm(
    state: StatementState, policy: LowConfidencePolicy = _DEFAULT_POLICY
) -> Literal["mark_awaiting_review", "store_transactions"]:
    """Pause for review only when the policy finds something to ask about.

    `policy` defaults to a fresh instance so this stays directly callable in
    tests as `route_after_llm(state)`, matching every other router in this
    module. The graph itself binds one shared `LowConfidencePolicy` instance
    here and into `ReviewLowConfidenceNode` via `functools.partial`, so "low
    confidence" has a single definition rather than two independently tuned
    ones.
    """
    transactions = state.get("transactions", [])
    if policy.select(transactions):
        return "mark_awaiting_review"
    return "store_transactions"
