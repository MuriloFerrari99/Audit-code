"""Modelos do OpenSquad: prontuário de raciocínio e disputas (Fase Agêntica).

Tenant-scoped (RLS) como o resto do dado de cliente. AgentReasoningLog dá a
explicabilidade exigida por grandes contas; Dispute registra a mitigação
automática (bloqueio em ERP / e-mail de contestação) do Agente Executor.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TENANT_SCOPED, Base, TimestampMixin, _uuid


class AgentReasoningLog(Base, TimestampMixin):
    """Passo de raciocínio de um agente do squad (auditável, imutável)."""

    __tablename__ = "agent_reasoning_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    # agrupa todos os passos de uma execução do squad (1 documento/lote)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(40), nullable=False)  # extractor|enricher|auditor|executor
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")  # started|ok|failed|skipped
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    reasoning_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    legal_citations: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # ["IN RFB 971/2009 art.112", ...]
    document_external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)


class Dispute(Base, TimestampMixin):
    """Ação de mitigação tomada pelo Agente Executor sobre um achado."""

    __tablename__ = "dispute"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    # draft|erp_blocked|email_sent|resolved|rejected|failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    channel: Mapped[str | None] = mapped_column(String(20), nullable=True)  # erp | email
    erp_action: Mapped[str | None] = mapped_column(String(40), nullable=True)  # block_payment...
    erp_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    recipient: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locale: Mapped[str | None] = mapped_column(String(10), nullable=True)  # pt-BR, en-US
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


# tenant-scoped -> RLS (como company/project, registro manual)
TENANT_SCOPED.update({"agent_reasoning_log", "dispute"})
