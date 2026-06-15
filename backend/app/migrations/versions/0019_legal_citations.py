"""explicabilidade: finding.legal_citations (base legal por achado)

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-15
"""

from __future__ import annotations

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE finding ADD COLUMN IF NOT EXISTS legal_citations JSONB")


def downgrade() -> None:
    op.execute("ALTER TABLE finding DROP COLUMN IF EXISTS legal_citations")
