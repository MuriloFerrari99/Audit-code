"""orçamento: qty_measured (medida/executada) para R4

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE budget_item ADD COLUMN IF NOT EXISTS qty_measured NUMERIC(18,4)")


def downgrade() -> None:
    op.execute("ALTER TABLE budget_item DROP COLUMN IF EXISTS qty_measured")
