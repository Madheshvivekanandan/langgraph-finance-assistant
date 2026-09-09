"""Add category, source, and confidence to transactions

Phase 2: categorizing transactions by keyword rules first, then an LLM.

The category set lives in a CHECK constraint rather than a lookup table: it is
small and stable, and keeping it here means the database, the rules engine, and
the model prompt cannot silently disagree. Adding a category needs a migration.

Existing rows get UNCATEGORIZED via a non-volatile server default, which
Postgres stores in the catalog, so the columns are added without a table rewrite.

Revision ID: 20260909_03
Revises: 20260908_02
Create Date: 2026-09-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260909_03"
down_revision: str | None = "20260908_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CATEGORIES = (
    "GROCERIES, DINING, TRANSPORT, HOUSING, UTILITIES, SHOPPING, ENTERTAINMENT, "
    "SUBSCRIPTIONS, HEALTH, EDUCATION, INVESTMENTS, TRANSFERS, CASH, FEES, INCOME, "
    "OTHER, UNCATEGORIZED"
)
_CATEGORY_LIST = ", ".join(f"'{name.strip()}'" for name in _CATEGORIES.split(","))


def upgrade() -> None:
    op.execute("SET lock_timeout = '3s'")

    op.add_column(
        "transactions",
        sa.Column("category", sa.String(length=20), nullable=False, server_default="UNCATEGORIZED"),
    )
    op.add_column(
        "transactions",
        sa.Column("categorized_by", sa.String(length=8), nullable=False, server_default="NONE"),
    )
    op.add_column(
        "transactions",
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=True),
    )

    op.create_check_constraint(
        "transactions_category_check", "transactions", f"category IN ({_CATEGORY_LIST})"
    )
    op.create_check_constraint(
        "transactions_categorized_by_check",
        "transactions",
        "categorized_by IN ('NONE', 'RULE', 'LLM', 'USER')",
    )
    # Null means "not predicted"; a stored value must be a real probability.
    op.create_check_constraint(
        "transactions_confidence_check",
        "transactions",
        "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
    )
    # A confidence only means something for a model's guess.
    op.create_check_constraint(
        "transactions_confidence_source_check",
        "transactions",
        "confidence IS NULL OR categorized_by = 'LLM'",
    )


def downgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    op.drop_constraint("transactions_confidence_source_check", "transactions")
    op.drop_constraint("transactions_confidence_check", "transactions")
    op.drop_constraint("transactions_categorized_by_check", "transactions")
    op.drop_constraint("transactions_category_check", "transactions")
    op.drop_column("transactions", "confidence")
    op.drop_column("transactions", "categorized_by")
    op.drop_column("transactions", "category")
