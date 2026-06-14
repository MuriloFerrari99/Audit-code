"""ajustes p/ ingest real do Sienge: resource_code + obra company_id nullable

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchase_order_item", sa.Column("resource_code", sa.String(64), nullable=True))
    op.create_index("ix_poi_resource_code", "purchase_order_item", ["resource_code"])
    op.add_column("budget_item", sa.Column("resource_code", sa.String(64), nullable=True))
    op.create_index("ix_budget_resource_code", "budget_item", ["resource_code"])
    op.alter_column("project", "company_id", existing_type=sa.dialects.postgresql.UUID(), nullable=True)
    op.create_index("ix_project_external_code", "project", ["external_code"])


def downgrade() -> None:
    op.drop_index("ix_project_external_code", "project")
    op.drop_index("ix_budget_resource_code", "budget_item")
    op.drop_index("ix_poi_resource_code", "purchase_order_item")
    op.drop_column("budget_item", "resource_code")
    op.drop_column("purchase_order_item", "resource_code")
    op.alter_column("project", "company_id", existing_type=sa.dialects.postgresql.UUID(), nullable=False)
