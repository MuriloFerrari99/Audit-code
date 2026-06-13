"""canônico, plataforma (raw/history/outbox), catálogo, achados, auth + RLS

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-13

Bootstrap greenfield: cria as tabelas restantes a partir do metadata
(checkfirst pula tenant/company/project já criadas em 0001) e aplica RLS às
novas tabelas tenant-scoped. Migrações futuras voltam ao fluxo normal de
autogenerate/op.create_table.
"""

from __future__ import annotations

from alembic import op

from app.models import TENANT_SCOPED, Base
from app.tenancy.rls import enable_rls_statements

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

# Já criadas e com RLS na 0001.
ALREADY = {"tenant", "company", "project"}


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    # Cria todas as tabelas do metadata que ainda não existem.
    Base.metadata.create_all(bind=bind, checkfirst=True)
    # RLS nas novas tabelas tenant-scoped.
    for table in sorted(TENANT_SCOPED - {"company", "project"}):
        for stmt in enable_rls_statements(table):
            op.execute(stmt)


def downgrade() -> None:
    bind = op.get_bind()
    # Remove só o que foi criado aqui (preserva tenancy da 0001).
    tables = [t for t in reversed(Base.metadata.sorted_tables) if t.name not in ALREADY]
    for t in tables:
        op.execute(f"DROP TABLE IF EXISTS {t.name} CASCADE;")
