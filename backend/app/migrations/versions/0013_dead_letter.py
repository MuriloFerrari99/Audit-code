"""dead_letter (A-3: nunca falhar em silêncio)

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op

from app.models import TENANT_SCOPED, Base
from app.tenancy.rls import enable_rls_statements

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)
    if "dead_letter" in TENANT_SCOPED:
        for stmt in enable_rls_statements("dead_letter"):
            op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS dead_letter CASCADE;")
