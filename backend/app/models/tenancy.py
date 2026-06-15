"""Hierarquia de tenancy (T-030): tenant -> company (CNPJ) -> project (obra).

Confirmado pelo founder: tenant = grupo/incorporadora; company = empresa/CNPJ;
project = empreendimento/obra. (modelo-dados.md §2.)
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, _uuid


class Tenant(Base, TimestampMixin):
    """Grupo/incorporadora — unidade de isolamento, billing e config.

    NÃO é TenantScoped (é a própria fronteira). Acesso controlado na app.
    """

    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    doc: Mapped[str | None] = mapped_column(String(20), nullable=True)  # CNPJ do grupo
    country_code: Mapped[str] = mapped_column(String(2), default="BR", nullable=False)
    # país/setor/moeda definem dinamicamente quais adapters/refs o sistema liga.
    currency: Mapped[str] = mapped_column(String(3), default="BRL", nullable=False)
    industry: Mapped[str] = mapped_column(String(40), default="construction", nullable=False)
    plan: Mapped[str] = mapped_column(String(40), default="mvp", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)


class Company(Base, TimestampMixin):
    """Empresa/CNPJ sob o tenant."""

    __tablename__ = "company"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(20), nullable=False)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)  # UF
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)


class Project(Base, TimestampMixin):
    """Empreendimento/obra — granularidade de orçamento, R$ exposto e relatórios."""

    __tablename__ = "project"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False, index=True
    )
    # Nullable: obras podem ser criadas como stub a partir do buildingId do
    # pedido antes de termos o vínculo com a empresa (Sienge não expõe o link).
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    external_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)  # UF p/ SINAPI regional
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    budget_total: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)


# Company e Project também são por-tenant. Como herdam de Base (não do
# TenantScopedMixin, para terem FKs explícitas), registramos a RLS manualmente.
from app.models.base import TENANT_SCOPED  # noqa: E402

TENANT_SCOPED.update({"company", "project"})
