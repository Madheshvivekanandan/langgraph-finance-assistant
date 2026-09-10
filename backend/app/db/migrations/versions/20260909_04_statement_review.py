"""Add AWAITING_REVIEW status and thread_id for human-in-the-loop review

Phase 5: the statement pipeline can now pause before storing low-confidence
LLM categorizations and resume from the same LangGraph checkpoint once a
person confirms or corrects them.

`thread_id` keys the LangGraph checkpoint the run can be resumed against. It
is nullable (a Studio run or the module-level graph may never persist one) and
unique - one thread belongs to at most one statement.

Revision ID: 20260909_04
Revises: 20260909_03
Create Date: 2026-09-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260909_04"
down_revision: str | None = "20260909_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DOWNGRADE_REASON = (
    "statement was awaiting review when human-in-the-loop review support was removed"
)


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")

    op.drop_constraint("statements_status_check", "statements")
    op.create_check_constraint(
        "statements_status_check",
        "statements",
        "status IN ('PROCESSING', 'AWAITING_REVIEW', 'COMPLETED', 'FAILED')",
    )

    op.add_column(
        "statements",
        sa.Column("thread_id", sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint("statements_thread_id_key", "statements", ["thread_id"])


def downgrade() -> None:
    op.execute("SET lock_timeout = '3s'")

    # The narrower three-value CHECK cannot coexist with an AWAITING_REVIEW row,
    # so any such row is moved to FAILED with an explanatory message first.
    op.execute(
        sa.text(
            "UPDATE statements SET status = 'FAILED', error_message = :reason "
            "WHERE status = 'AWAITING_REVIEW'"
        ).bindparams(reason=_DOWNGRADE_REASON)
    )

    op.drop_constraint("statements_thread_id_key", "statements")
    op.drop_column("statements", "thread_id")

    op.drop_constraint("statements_status_check", "statements")
    op.create_check_constraint(
        "statements_status_check",
        "statements",
        "status IN ('PROCESSING', 'COMPLETED', 'FAILED')",
    )
