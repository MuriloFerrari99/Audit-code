"""counterparty (integridade de fornecedor — dim.4)

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op

from app.models import Base

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS counterparty CASCADE;")
