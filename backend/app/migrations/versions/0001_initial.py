"""inicial: extensões, tenancy (tenant/company/project) e RLS

Revision ID: 0001
Revises:
Create Date: 2026-06-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.tenancy.rls import enable_rls_statements

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

RLS_TABLES = ["company", "project"]


def upgrade() -> None:
    # Extensões necessárias (pgvector entra quando o catálogo for criado).
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    op.create_table(
        "tenant",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("doc", sa.String(20), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=False, server_default="BR"),
        sa.Column("plan", sa.String(40), nullable=False, server_default="mvp"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "company",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"),
                  nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("cnpj", sa.String(20), nullable=False),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "project",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenant.id"),
                  nullable=False, index=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company.id"),
                  nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("external_code", sa.String(64), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("budget_total", sa.Numeric(18, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # RLS por tenant (ADR-08). tenant não tem RLS (é a fronteira).
    for table in RLS_TABLES:
        for stmt in enable_rls_statements(table):
            op.execute(stmt)


def downgrade() -> None:
    op.drop_table("project")
    op.drop_table("company")
    op.drop_table("tenant")
