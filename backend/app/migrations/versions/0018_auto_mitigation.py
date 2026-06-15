"""mitigação automática: tenant.auto_mitigation (opt-in, default OFF)

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-15
"""

from __future__ import annotations

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE tenant ADD COLUMN IF NOT EXISTS auto_mitigation BOOLEAN NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE tenant DROP COLUMN IF EXISTS auto_mitigation")
