"""cotação: resource_code (productId) para R2/R6

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE quotation ADD COLUMN IF NOT EXISTS resource_code VARCHAR(64)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_quotation_resource_code ON quotation (resource_code)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_quotation_resource_code")
    op.execute("ALTER TABLE quotation DROP COLUMN IF EXISTS resource_code")
