"""upload NF-e: invoice_item + retenções (INSS/ISS) na nota

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op

from app.models import TENANT_SCOPED, Base
from app.tenancy.rls import enable_rls_statements

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE invoice ADD COLUMN IF NOT EXISTS inss_retention NUMERIC(18,4)")
    op.execute("ALTER TABLE invoice ADD COLUMN IF NOT EXISTS iss_retention NUMERIC(18,4)")
    op.execute("ALTER TABLE invoice ADD COLUMN IF NOT EXISTS is_service BOOLEAN")
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)  # cria invoice_item
    if "invoice_item" in TENANT_SCOPED:
        for stmt in enable_rls_statements("invoice_item"):
            op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS invoice_item CASCADE")
    for c in ("inss_retention", "iss_retention", "is_service"):
        op.execute(f"ALTER TABLE invoice DROP COLUMN IF EXISTS {c}")
