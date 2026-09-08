"""Baseline: empty schema anchor so later migrations have a fixed starting point.

Revision ID: 20260908_01
Revises:
Create Date: 2026-09-08

"""

from collections.abc import Sequence

revision: str = "20260908_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
