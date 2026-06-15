"""cobrança: plan (global) + subscription + usage_counter (tenant-scoped)

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op

from app.models import TENANT_SCOPED, Base
from app.tenancy.rls import enable_rls_statements

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # cria plan, subscription, usage_counter (e quaisquer tabelas ainda ausentes)
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)
    for table in ("subscription", "usage_counter"):
        if table in TENANT_SCOPED:
            for stmt in enable_rls_statements(table):
                op.execute(stmt)


def downgrade() -> None:
    for t in ("usage_counter", "subscription", "plan"):
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
