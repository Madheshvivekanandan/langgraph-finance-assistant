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
) -> Literal["store_transactions", "record_failure"]:
    """Continue to storage unless normalization recorded an error."""
    return "record_failure" if state.get("error") else "store_transactions"
