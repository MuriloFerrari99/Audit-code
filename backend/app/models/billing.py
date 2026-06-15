"""Cobrança (Fase 2) — planos, assinatura e medição de uso.

Modelo de negócio (gtm.md): mensalidade base + excedente por nota acima do
limite do plano (overage). A fatura mensal é calculada do USO REAL de uploads
(usage_counter), não estimada. Ver docs/fase-2-monetizacao.md.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TENANT_SCOPED, Base, TimestampMixin, _uuid

MONEY = Numeric(18, 4)


class Plan(Base, TimestampMixin):
    """Catálogo de planos — GLOBAL (não é tenant-scoped; read-only p/ o tenant)."""

    __tablename__ = "plan"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_price: Mapped[float] = mapped_column(MONEY, nullable=False, default=0)
    # Nº de notas/mês incluídas na mensalidade; acima disso cobra overage_price/nota.
    invoice_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overage_price: Mapped[float] = mapped_column(MONEY, nullable=False, default=0)
    gainshare_pct: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    features: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Subscription(Base, TimestampMixin):
    """Assinatura do tenant a um plano (tenant-scoped)."""

    __tablename__ = "subscription"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plan.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Integração com provedor de pagamento (preenchido na fatia 3; agnóstico).
    provider: Mapped[str | None] = mapped_column(String(30), nullable=True)
    provider_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)


class UsageCounter(Base, TimestampMixin):
    """Medição de uso por tenant e período (AAAA-MM). Vínculo com o upload real."""

    __tablename__ = "usage_counter"
    __table_args__ = (UniqueConstraint("tenant_id", "period", name="uq_usage_tenant_period"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # 'AAAA-MM'
    invoices_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    findings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_marker: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# subscription e usage_counter são por-tenant -> RLS. plan é global (sem RLS).
TENANT_SCOPED.update({"subscription", "usage_counter"})
