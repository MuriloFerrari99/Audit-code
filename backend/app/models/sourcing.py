"""Entidades canônicas da cadeia auditável (T-044, modelo-dados.md §4/§6).

Cadeia: budget_item -> quotation / purchase_request -> purchase_order
        -> invoice/delivery -> bill/payment ; creditor referenciado.

Dinheiro em NUMERIC(18,4) (ADR-04). Toda entidade é tenant-scoped (RLS) e tem
chave natural única (tenant_id, source, source_external_id) p/ idempotência.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TENANT_SCOPED, Base, SourcedMixin, TenantScopedMixin

MONEY = Numeric(18, 4)
QTY = Numeric(18, 4)

CANONICAL_TABLES = [
    "creditor",
    "budget_item",
    "quotation",
    "purchase_request",
    "purchase_request_item",
    "purchase_order",
    "purchase_order_item",
    "order_authorization",
    "invoice",
    "bill",
]
TENANT_SCOPED.update(CANONICAL_TABLES)


def _natural_key(table: str) -> UniqueConstraint:
    return UniqueConstraint("tenant_id", "source", "source_external_id", name=f"uq_{table}_natural")


class Creditor(Base, TenantScopedMixin, SourcedMixin):
    __tablename__ = "creditor"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    cnpj_cpf: Mapped[str | None] = mapped_column(String(20), nullable=True)
    kind: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Fase 1 (integridade): preenchido pela dimensão 4.
    integrity_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    __table_args__ = (_natural_key("creditor"),)


class BudgetItem(Base, TenantScopedMixin, SourcedMixin):
    __tablename__ = "budget_item"
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    resource_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    raw_description: Mapped[str] = mapped_column(String(500), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    qty_budgeted: Mapped[float | None] = mapped_column(QTY, nullable=True)
    unit_price_budgeted: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    total_budgeted: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    __table_args__ = (_natural_key("budget_item"),)


class Quotation(Base, TenantScopedMixin, SourcedMixin):
    __tablename__ = "quotation"
    creditor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    raw_description: Mapped[str] = mapped_column(String(500), nullable=False)
    qty: Mapped[float | None] = mapped_column(QTY, nullable=True)
    unit_price: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    negotiation_round: Mapped[int | None] = mapped_column(nullable=True)
    __table_args__ = (_natural_key("quotation"),)


class PurchaseRequest(Base, TenantScopedMixin, SourcedMixin):
    __tablename__ = "purchase_request"
    requested_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    __table_args__ = (_natural_key("purchase_request"),)


class PurchaseRequestItem(Base, TenantScopedMixin):
    __tablename__ = "purchase_request_item"
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    raw_description: Mapped[str] = mapped_column(String(500), nullable=False)
    qty: Mapped[float | None] = mapped_column(QTY, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)


class PurchaseOrder(Base, TenantScopedMixin, SourcedMixin):
    __tablename__ = "purchase_order"
    creditor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    total: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ordered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (_natural_key("purchase_order"),)


class PurchaseOrderItem(Base, TenantScopedMixin):
    __tablename__ = "purchase_order_item"
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Código do insumo na fonte (resourceId do Sienge): chave de comparação
    # intra-tenant para R1/R4 sem depender do casamento de catálogo (ML).
    resource_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    raw_description: Mapped[str] = mapped_column(String(500), nullable=False)
    qty: Mapped[float | None] = mapped_column(QTY, nullable=True)
    unit_price: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    total: Mapped[float | None] = mapped_column(MONEY, nullable=True)


class OrderAuthorization(Base, TenantScopedMixin):
    """Histórico de autorização/alçada — chave para fracionamento e sem concorrência."""

    __tablename__ = "order_authorization"
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    authorized_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    threshold_at_time: Mapped[float | None] = mapped_column(MONEY, nullable=True)


class Invoice(Base, TenantScopedMixin, SourcedMixin):
    """Nota / atendimento ao pedido (deliveries-attended)."""

    __tablename__ = "invoice"
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    creditor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    number: Mapped[str | None] = mapped_column(String(60), nullable=True)
    qty_delivered: Mapped[float | None] = mapped_column(QTY, nullable=True)
    unit_price_invoiced: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    total_invoiced: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Fase 1 (dimensão fiscal):
    nfe_key: Mapped[str | None] = mapped_column(String(60), nullable=True)
    nfe_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    __table_args__ = (_natural_key("invoice"),)


class Bill(Base, TenantScopedMixin, SourcedMixin):
    """Título / pagamento (contas a pagar)."""

    __tablename__ = "bill"
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    creditor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    amount: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Fase 1 (dimensão pagamento):
    paid_account: Mapped[str | None] = mapped_column(String(60), nullable=True)
    openfinance_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    __table_args__ = (_natural_key("bill"),)
