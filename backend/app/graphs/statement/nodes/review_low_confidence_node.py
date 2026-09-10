"""Graph node: pause for a person to confirm or correct low-confidence categories."""

import logging
from dataclasses import replace
from typing import Any

from langgraph.types import interrupt

from app.domain.categorization_source import CategorizationSource
from app.domain.low_confidence_policy import LowConfidencePolicy
from app.domain.transaction_category import TransactionCategory
from app.graphs.statement.state import StatementState

logger = logging.getLogger(__name__)

_DEFAULT_FILENAME = "statement.csv"


class ReviewLowConfidenceNode:
    """Surfaces low-confidence LLM guesses to a person before they are stored.

    No database access, deliberately: LangGraph resumes an interrupted node by
    re-running it from its first line, with `interrupt()` returning the resume
    value instead of suspending again. Anything before the `interrupt()` call
    therefore executes a second time on resume - a database write here would
    run twice. The one side effect on this path (setting the statement's
    status) lives in `MarkAwaitingReviewNode`, which runs once, immediately
    before this node.
    """

    def __init__(self, policy: LowConfidencePolicy) -> None:
        self._policy = policy

    def __call__(self, state: StatementState) -> dict[str, object]:
        """Ask a person to confirm or correct the rows the policy flagged.

        Returns `reviewed_count: 0` with no other change when nothing is
        flagged - defensive, since the router should already have skipped this
        node in that case.
        """
        transactions = state["transactions"]
        pending_positions = self._policy.select(transactions)
        if not pending_positions:
            return {"reviewed_count": 0}

        payload = {
            "statement_id": state["statement_id"],
            "filename": state.get("filename") or _DEFAULT_FILENAME,
            "threshold": str(self._policy.threshold),
            "items": [
                {
                    "index": position,
                    "transaction_date": transactions[position].transaction_date.isoformat(),
                    "description": transactions[position].description,
                    "amount": str(transactions[position].amount),
                    "direction": transactions[position].direction.value,
                    "suggested_category": transactions[position].category.value,
                    "confidence": str(transactions[position].confidence),
                }
                for position in pending_positions
            ],
        }

        resume: dict[str, Any] = interrupt(payload)
        decisions = {int(item["index"]): item["category"] for item in resume.get("decisions", [])}

        updated = list(transactions)
        for index, category_name in decisions.items():
            updated[index] = replace(
                updated[index],
                category=TransactionCategory(category_name),
                categorized_by=CategorizationSource.USER,
                confidence=None,
            )

        logger.info(
            "statement_review_resolved",
            extra={
                "statement_id": state["statement_id"],
                "reviewed": len(pending_positions),
                "corrected": len(decisions),
            },
        )
        return {"transactions": updated, "reviewed_count": len(pending_positions)}
