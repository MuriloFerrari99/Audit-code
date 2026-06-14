"""rule_calibration (Módulo C — calibração por tenant)

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op

from app.models import TENANT_SCOPED, Base
from app.tenancy.rls import enable_rls_statements

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)
    if "rule_calibration" in TENANT_SCOPED:
        for stmt in enable_rls_statements("rule_calibration"):
            op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS rule_calibration CASCADE;")
