"""finding.confidence (Módulo B — score de confiança)

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("finding", sa.Column("confidence", sa.Numeric(4, 3), nullable=True))


def downgrade() -> None:
    op.drop_column("finding", "confidence")
