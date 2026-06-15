"""invoice: campos fiscais (Fase A — dim.2)

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_COLS = [
    ("series", "VARCHAR(20)"),
    ("products_amount", "NUMERIC(18,4)"),
    ("ipi_tax", "NUMERIC(18,4)"),
    ("icms_st_tax", "NUMERIC(18,4)"),
    ("consistency", "VARCHAR(2)"),
    ("eletronic_invoice_id", "VARCHAR(60)"),
    ("bill_external", "VARCHAR(64)"),
]


def upgrade() -> None:
    for name, typ in _COLS:
        op.execute(f"ALTER TABLE invoice ADD COLUMN IF NOT EXISTS {name} {typ}")
    op.execute("CREATE INDEX IF NOT EXISTS ix_invoice_bill_external ON invoice (bill_external)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_invoice_bill_external")
    for name, _ in _COLS:
        op.execute(f"ALTER TABLE invoice DROP COLUMN IF EXISTS {name}")
