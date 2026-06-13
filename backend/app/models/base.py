"""Base ORM + mixins comuns (ADR-04/05/20, T-045).

- `Base`: DeclarativeBase do SQLAlchemy 2.0.
- `TimestampMixin`: created_at/updated_at em UTC.
- `TenantScopedMixin`: tenant_id + colunas de origem/versionamento; toda entidade
  de dado de cliente herda dela e recebe policy RLS (ver tenancy.apply_rls).
- `TENANT_SCOPED`: registro das tabelas que precisam de RLS.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# Tabelas de dado de cliente que devem ter RLS habilitado.
TENANT_SCOPED: set[str] = set()


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TenantScopedMixin(TimestampMixin):
    """Campos comuns a toda entidade de dado de cliente (modelo-dados.md §5)."""

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    # Abstração país/vertical (latam-readiness.md) — só BR/BRL hoje.
    country_code: Mapped[str] = mapped_column(String(2), default="BR", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="BRL", nullable=False)

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        tablename = getattr(cls, "__tablename__", None)
        if tablename:
            TENANT_SCOPED.add(tablename)


class SourcedMixin:
    """Para entidades que vêm de uma fonte externa (ERP/NF-e/...)."""

    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="sienge", nullable=False)
    source_external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
