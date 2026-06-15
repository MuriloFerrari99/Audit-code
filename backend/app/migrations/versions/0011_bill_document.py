"""bill: document_number/document_identification (dim.3 P1)

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE bill ADD COLUMN IF NOT EXISTS document_number VARCHAR(60)")
    op.execute("ALTER TABLE bill ADD COLUMN IF NOT EXISTS document_identification VARCHAR(20)")


def downgrade() -> None:
    op.execute("ALTER TABLE bill DROP COLUMN IF EXISTS document_identification")
    op.execute("ALTER TABLE bill DROP COLUMN IF EXISTS document_number")
