"""Tabelas de plataforma: raw landing, histórico, outbox (ADR-06/20/01).

- raw_record: zona de pouso bruta append-only (reprocessar sem re-puxar a fonte).
- entity_history: snapshots append-only por mudança de conteúdo.
- outbox_event: evento na MESMA transação da escrita do canônico; o worker
  consome e enfileira reavaliação de regras.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TENANT_SCOPED, Base, TimestampMixin, _uuid


class RawRecord(Base):
    __tablename__ = "raw_record"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_raw_natural", "tenant_id", "source", "entity_type", "source_external_id"),
    )


class EntityHistory(Base):
    __tablename__ = "entity_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(48), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    version: Mapped[int] = mapped_column(nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class OutboxEvent(Base):
    __tablename__ = "outbox_event"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(48), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    change_type: Mapped[str] = mapped_column(String(16), nullable=False)  # created|updated
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_outbox_unprocessed", "processed_at"),)


class TenantSecret(Base, TimestampMixin):
    """Segredo por tenant (ex.: credencial Sienge), CRIPTOGRAFADO em repouso.

    Tabela de plataforma — acessada pelo role dono com filtro explícito de tenant;
    valor cifrado com Fernet (app.core.crypto). Não guardar credencial em texto.
    """

    __tablename__ = "tenant_secret"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(200), nullable=False)
    value_enc: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "path", name="uq_tenant_secret"),)


# Todas têm tenant_id e devem ter RLS (exceto tenant_secret, que é plataforma).
TENANT_SCOPED.update({"raw_record", "entity_history", "outbox_event"})
