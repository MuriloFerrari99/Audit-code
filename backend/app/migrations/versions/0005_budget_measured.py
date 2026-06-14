"""orçamento: qty_measured (medida/executada) para R4

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("budget_item", sa.Column("qty_measured", sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("budget_item", "qty_measured")
