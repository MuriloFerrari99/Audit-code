"""cotação: resource_code (productId) para R2/R6

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("quotation", sa.Column("resource_code", sa.String(64), nullable=True))
    op.create_index("ix_quotation_resource_code", "quotation", ["resource_code"])


def downgrade() -> None:
    op.drop_index("ix_quotation_resource_code", "quotation")
    op.drop_column("quotation", "resource_code")
