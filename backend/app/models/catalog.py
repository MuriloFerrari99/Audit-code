"""Catálogo canônico de insumos e mapeamento por tenant (T-046, ADR-16).

- catalog_item: referência PURA, semeada do SINAPI. NÃO contém dado de tenant;
  é compartilhável (sem RLS).
- item_mapping: descrição-do-cliente -> catalog_item. É por tenant (com RLS).

embedding usa pgvector. A dimensão depende do modelo de embeddings (a definir —
ver perguntas-abertas A6). EMBEDDING_DIM é ajustável antes do 1º embed.
"""

from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TENANT_SCOPED, Base, TenantScopedMixin, _uuid

EMBEDDING_DIM = 1536  # ajustar conforme o modelo de embeddings escolhido (A6)


class CatalogItem(Base):
    """Insumo canônico (referência). Sem tenant_id — compartilhável."""

    __tablename__ = "catalog_item"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    canonical_name: Mapped[str] = mapped_column(String(300), nullable=False)
    vertical: Mapped[str] = mapped_column(String(40), default="construcao", nullable=False)
    sinapi_code: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    spec_attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)


class ItemMapping(Base, TenantScopedMixin):
    """Mapeamento descrição crua -> catálogo, por tenant (rótulo de ML)."""

    __tablename__ = "item_mapping"

    raw_description: Mapped[str] = mapped_column(String(500), nullable=False)
    catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(10), default="ml", nullable=False)  # ml | human
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)


TENANT_SCOPED.add("item_mapping")
