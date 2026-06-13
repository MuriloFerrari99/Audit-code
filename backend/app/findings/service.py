"""Serviço de achados: revisão humana (rótulo), ledger de gainshare e trilha.

Revisão = rótulo (Camada 3). Aceitar move exposto -> validado no value_ledger
(gtm.md, fase MVP). Ledger é imutável; reversões entram como true-up.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.core.timeutils import now_utc, period_key
from app.models.findings import (
    AuditLog,
    Finding,
    FindingEvidence,
    FindingReview,
    FindingStatus,
    ValueLedger,
)

DECISION_TO_STATUS = {
    "accept": FindingStatus.ACCEPTED.value,
    "dismiss": FindingStatus.DISMISSED.value,
    "escalate": FindingStatus.ESCALATED.value,
}


def list_findings(
    session: Session,
    status: str | None = None,
    project_id: str | None = None,
    rule_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Finding]:
    stmt = select(Finding)
    if status:
        stmt = stmt.where(Finding.status == status)
    if project_id:
        stmt = stmt.where(Finding.project_id == project_id)
    if rule_id:
        stmt = stmt.where(Finding.rule_id == rule_id)
    stmt = stmt.order_by(Finding.exposed_amount.desc().nullslast()).limit(limit).offset(offset)
    return list(session.execute(stmt).scalars())


def get_evidence(session: Session, finding_id: str) -> list[FindingEvidence]:
    return list(
        session.execute(
            select(FindingEvidence).where(FindingEvidence.finding_id == finding_id)
        ).scalars()
    )


def review_finding(
    session: Session,
    tenant_id: str,
    finding_id: str,
    decision: str,
    reviewed_by: str,
    reason: str | None = None,
) -> Finding:
    if decision not in DECISION_TO_STATUS:
        raise DomainError(f"decisão inválida: {decision}")
    finding = session.get(Finding, finding_id)
    if finding is None:
        raise DomainError("achado não encontrado")

    finding.status = DECISION_TO_STATUS[decision]
    session.add(
        FindingReview(
            tenant_id=tenant_id,
            finding_id=finding.id,
            decision=decision,
            reason=reason,
            reviewed_by=reviewed_by,
        )
    )

    # Gainshare (MVP): aceitar valida o R$ exposto.
    if decision == "accept" and finding.exposed_amount is not None:
        session.add(
            ValueLedger(
                tenant_id=tenant_id,
                project_id=finding.project_id,
                finding_id=finding.id,
                exposed_amount=finding.exposed_amount,
                validated_amount=finding.exposed_amount,
                realized_amount=None,  # Realizado exige sanar no ciclo seguinte (Q3)
                period=period_key(now_utc()),
                entry_type="accrual",
                baseline_snapshot=finding.reference_snapshot,
                status="validated",
            )
        )

    session.add(
        AuditLog(
            tenant_id=tenant_id,
            actor="user",
            actor_id=reviewed_by,
            action=f"finding.{decision}",
            target_type="finding",
            target_id=str(finding.id),
            audit_metadata={"reason": reason},
        )
    )
    return finding
