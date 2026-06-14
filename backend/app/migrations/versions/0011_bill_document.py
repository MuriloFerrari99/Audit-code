"""bill: document_number/document_identification (dim.3 P1)

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("bill", sa.Column("document_number", sa.String(60), nullable=True))
    op.add_column("bill", sa.Column("document_identification", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("bill", "document_identification")
    op.drop_column("bill", "document_number")
