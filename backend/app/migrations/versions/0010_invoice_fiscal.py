"""invoice: campos fiscais (Fase A — dim.2)

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_COLS = [
    ("series", sa.String(20)),
    ("products_amount", sa.Numeric(18, 4)),
    ("ipi_tax", sa.Numeric(18, 4)),
    ("icms_st_tax", sa.Numeric(18, 4)),
    ("consistency", sa.String(2)),
    ("eletronic_invoice_id", sa.String(60)),
    ("bill_external", sa.String(64)),
]


def upgrade() -> None:
    for name, typ in _COLS:
        op.add_column("invoice", sa.Column(name, typ, nullable=True))
    op.create_index("ix_invoice_bill_external", "invoice", ["bill_external"])


def downgrade() -> None:
    op.drop_index("ix_invoice_bill_external", "invoice")
    for name, _ in _COLS:
        op.drop_column("invoice", name)
