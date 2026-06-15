"""ajustes p/ ingest real do Sienge: resource_code + obra company_id nullable

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-13

Idempotente (IF NOT EXISTS): a 0002 usa create_all() com o metadata atual, que já
cria estas colunas; estas migrações só garantem a presença num banco legado.
"""

from __future__ import annotations

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE purchase_order_item ADD COLUMN IF NOT EXISTS resource_code VARCHAR(64)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_poi_resource_code ON purchase_order_item (resource_code)")
    op.execute("ALTER TABLE budget_item ADD COLUMN IF NOT EXISTS resource_code VARCHAR(64)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_budget_resource_code ON budget_item (resource_code)")
    op.execute("ALTER TABLE project ALTER COLUMN company_id DROP NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_project_external_code ON project (external_code)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_project_external_code")
    op.execute("DROP INDEX IF EXISTS ix_budget_resource_code")
    op.execute("DROP INDEX IF EXISTS ix_poi_resource_code")
    op.execute("ALTER TABLE budget_item DROP COLUMN IF EXISTS resource_code")
    op.execute("ALTER TABLE purchase_order_item DROP COLUMN IF EXISTS resource_code")
