"""sinapi_reference (Camada 1 de preço)

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op

from app.models import Base

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sinapi_reference CASCADE;")
