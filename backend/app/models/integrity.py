"""Cadastro de contraparte (CNPJ) — Dimensão 4. Ver docs/modulo-integridade.md.

Dado PÚBLICO e o mesmo para todos os tenants (situação, sanções, QSA) → tabela
COMPARTILHADA, SEM RLS (como catalog_item/sinapi_reference). O vínculo
"tenant comprou de X" é o achado (tenant-scoped), não esta tabela.

`status` garante a confiabilidade: 'ok' (consultado), 'indisponivel' (fonte fora)
ou 'erro'. NUNCA inferir "sem sanção" a partir de falha — ver service.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, _uuid


class Counterparty(Base):
    __tablename__ = "counterparty"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    cnpj: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    razao_social: Mapped[str | None] = mapped_column(String(300), nullable=True)
    situacao_cadastral: Mapped[str | None] = mapped_column(String(40), nullable=True)
    data_abertura: Mapped[str | None] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    cnae: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sancoes: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # [{fonte,tipo,orgao,...}]
    qsa: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # sócios minimizados (LGPD)
    status: Mapped[str] = mapped_column(String(20), default="ok", nullable=False)
    source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
