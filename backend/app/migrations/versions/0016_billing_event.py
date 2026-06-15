"""cobrança: billing_event (linha de fatura materializada, tenant-scoped)

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op

from app.models import TENANT_SCOPED, Base
from app.tenancy.rls import enable_rls_statements

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)
    if "billing_event" in TENANT_SCOPED:
        for stmt in enable_rls_statements("billing_event"):
            op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS billing_event CASCADE")
