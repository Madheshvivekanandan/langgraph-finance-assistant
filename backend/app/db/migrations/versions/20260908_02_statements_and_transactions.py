"""Add statements and transactions tables

Phase 1: ingesting a CSV bank statement into typed transaction rows.

Assumption stated explicitly: amounts are single-currency (INR) for now, so no
currency column. Adding one later is an additive, non-breaking change.

Revision ID: 20260908_02
Revises: 20260908_01
Create Date: 2026-09-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_02"
down_revision: str | None = "20260908_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Never let this migration queue behind a long-running query and then block
    # every reader behind itself.
    op.execute("SET lock_timeout = '3s'")

    op.create_table(
        "statements",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("transaction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="statements_pkey"),
        sa.UniqueConstraint("file_hash", name="statements_file_hash_key"),
        sa.CheckConstraint(
            "status IN ('PROCESSING', 'COMPLETED', 'FAILED')",
            name="statements_status_check",
        ),
        sa.CheckConstraint("transaction_count >= 0", name="statements_transaction_count_check"),
        # Either both period bounds are set or neither is, and they are ordered.
        sa.CheckConstraint(
            "(period_start IS NULL) = (period_end IS NULL) "
            "AND (period_start IS NULL OR period_start <= period_end)",
            name="statements_period_check",
        ),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("statement_id", sa.BigInteger(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="transactions_pkey"),
        sa.ForeignKeyConstraint(
            ["statement_id"],
            ["statements.id"],
            name="transactions_statement_id_fkey",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("amount > 0", name="transactions_amount_positive_check"),
        sa.CheckConstraint("direction IN ('DEBIT', 'CREDIT')", name="transactions_direction_check"),
    )

    # Postgres does not index FK child columns for you; without this a statement
    # delete scans the whole transactions table.
    op.create_index("transactions_statement_id_idx", "transactions", ["statement_id"])
    # Serves the transaction list endpoint's keyset pagination, which orders by
    # (transaction_date DESC, id DESC).
    op.create_index(
        "transactions_transaction_date_id_idx",
        "transactions",
        [sa.text("transaction_date DESC"), sa.text("id DESC")],
    )

    # updated_at is maintained by the database, not by application code, so any
    # writer (a backfill, a psql session) keeps it honest.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER statements_set_updated_at
        BEFORE UPDATE ON statements
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute("SET lock_timeout = '3s'")
    op.execute("DROP TRIGGER IF EXISTS statements_set_updated_at ON statements")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
    op.drop_index("transactions_transaction_date_id_idx", table_name="transactions")
    op.drop_index("transactions_statement_id_idx", table_name="transactions")
    op.drop_table("transactions")
    op.drop_table("statements")
