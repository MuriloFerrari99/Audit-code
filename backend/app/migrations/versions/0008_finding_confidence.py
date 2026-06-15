"""finding.confidence (Módulo B — score de confiança)

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE finding ADD COLUMN IF NOT EXISTS confidence NUMERIC(4,3)")


def downgrade() -> None:
    op.execute("ALTER TABLE finding DROP COLUMN IF EXISTS confidence")
