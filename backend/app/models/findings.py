"""Entidades de produto: achados, evidência, revisão, config, ledger, auditoria.

Implementa o ciclo de vida do achado (ADR-02), dedup_key (ADR-03) e snapshots
de config/referência (ADR-07). value_ledger é imutável; reversões via true-up.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TENANT_SCOPED, Base, TenantScopedMixin, TimestampMixin, _uuid

MONEY = Numeric(18, 4)


class FindingStatus(str, enum.Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    ESCALATED = "escalated"
    RESOLVED = "resolved"  # condição deixou de valer (dado corrigido)
    SUPERSEDED = "superseded"  # recalculado por nova versão de regra


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Finding(Base, TenantScopedMixin):
    __tablename__ = "finding"

    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    rule_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    rule_version: Mapped[int] = mapped_column(default=1, nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(80), nullable=False)  # ADR-03
    severity: Mapped[str] = mapped_column(String(10), default=Severity.MEDIUM.value, nullable=False)
    status: Mapped[str] = mapped_column(String(12), default=FindingStatus.OPEN.value, nullable=False)
    exposed_amount: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    # Score de confiança (Módulo B): baixo -> "a investigar", não vai p/ cliente.
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    # Explicabilidade/reprodutibilidade (ADR-07):
    reference_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    config_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("tenant_id", "dedup_key", name="uq_finding_dedup"),)


class FindingEvidence(Base, TenantScopedMixin):
    """Liga o achado às linhas canônicas exatas que o originaram."""

    __tablename__ = "finding_evidence"

    finding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(48), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    role: Mapped[str] = mapped_column(String(40), nullable=False)  # pedido|cotacao_mais_barata|...
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)  # texto citável
    value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class FindingReview(Base, TenantScopedMixin):
    """Decisão humana = rótulo (Camada 3). Sticky (ADR-02)."""

    __tablename__ = "finding_review"

    finding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(12), nullable=False)  # accept|dismiss|escalate
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(120), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RuleConfig(Base, TenantScopedMixin):
    """Threshold por tenant (default global tem tenant_id sentinela 0)."""

    __tablename__ = "rule_config"

    rule_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)


class RuleCalibration(Base, TenantScopedMixin):
    """Calibração por (tenant, regra) aprendida do feedback (Módulo C)."""

    __tablename__ = "rule_calibration"

    rule_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    samples: Mapped[int] = mapped_column(default=0, nullable=False)
    accepted: Mapped[int] = mapped_column(default=0, nullable=False)
    dismissed: Mapped[int] = mapped_column(default=0, nullable=False)
    acceptance_rate: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    confidence_factor: Mapped[float] = mapped_column(Numeric(4, 3), default=1.0, nullable=False)
    __table_args__ = (UniqueConstraint("tenant_id", "rule_id", name="uq_rule_calibration"),)


class ValueLedger(Base, TenantScopedMixin):
    """Ledger de gainshare (gtm.md). Imutável; reversão entra como nova linha."""

    __tablename__ = "value_ledger"

    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    exposed_amount: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    validated_amount: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    realized_amount: Mapped[float | None] = mapped_column(MONEY, nullable=True)
    period: Mapped[str | None] = mapped_column(String(7), nullable=True)  # YYYY-MM
    entry_type: Mapped[str] = mapped_column(String(16), default="accrual", nullable=False)  # accrual|true_up
    baseline_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)


class AuditLog(Base, TimestampMixin):
    """Trilha do próprio sistema (ADR-18). Append-only, inclui tenant quando houver."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(20), nullable=False)  # user|system|agent
    actor_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    audit_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


# audit_log NÃO tem RLS por tenant (pode ter linhas de sistema sem tenant);
# acesso é controlado na app. As demais são tenant-scoped.
TENANT_SCOPED.update(
    {
        "finding",
        "finding_evidence",
        "finding_review",
        "rule_config",
        "value_ledger",
        "rule_calibration",
    }
)
