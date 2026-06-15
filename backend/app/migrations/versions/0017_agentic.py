"""OpenSquad: agent_reasoning_log + dispute + tenant.industry/currency

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-15
"""

from __future__ import annotations

from alembic import op

from app.models import TENANT_SCOPED, Base
from app.tenancy.rls import enable_rls_statements

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tenant ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'BRL'")
    op.execute(
        "ALTER TABLE tenant ADD COLUMN IF NOT EXISTS industry VARCHAR(40) "
        "NOT NULL DEFAULT 'construction'"
    )
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)
    for table in ("agent_reasoning_log", "dispute"):
        if table in TENANT_SCOPED:
            for stmt in enable_rls_statements(table):
                op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agent_reasoning_log CASCADE")
    op.execute("DROP TABLE IF EXISTS dispute CASCADE")
    for c in ("industry", "currency"):
        op.execute(f"ALTER TABLE tenant DROP COLUMN IF EXISTS {c}")
