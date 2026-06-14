"""tenant_secret (credenciais por tenant, criptografadas)

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op

from app.models import Base

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_secret CASCADE;")
