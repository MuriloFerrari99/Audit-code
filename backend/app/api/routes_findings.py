"""Rotas de achados e disparo de regras (E13)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_role
from app.api.schemas import EvidenceOut, FindingOut, ReviewIn
from app.core.errors import DomainError
from app.core.metrics import findings_emitted_total, rule_runs_total
from app.findings.service import get_evidence, list_findings, review_finding
from app.models.findings import Role
from app.rules.engine import run_all

router = APIRouter(tags=["findings"])


def _to_out(finding, evidence=None) -> FindingOut:
    return FindingOut(
        id=str(finding.id),
        rule_id=finding.rule_id,
        severity=finding.severity,
        status=finding.status,
        exposed_amount=finding.exposed_amount,
        title=finding.title,
        project_id=str(finding.project_id) if finding.project_id else None,
        created_at=finding.created_at,
        evidence=[
            EvidenceOut(entity_type=e.entity_type, role=e.role, snippet=e.snippet, value=e.value)
            for e in (evidence or [])
        ],
    )


@router.post("/rules/run")
def trigger_rules(
    db: Session = Depends(get_tenant_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Roda todas as regras para o tenant atual (MVP: disparo manual; em prod o
    worker dispara via outbox)."""
    summary = run_all(db, user.tenant_id)
    rule_runs_total.labels(tenant=user.tenant_id).inc()
    for rule_id, n in summary.items():
        if n:
            findings_emitted_total.labels(rule_id=rule_id).inc(n)
    return {"tenant_id": user.tenant_id, "found": summary}


@router.get("/findings", response_model=list[FindingOut])
def get_findings(
    db: Session = Depends(get_tenant_db),
    status_: str | None = Query(default=None, alias="status"),
    project_id: str | None = None,
    rule_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[FindingOut]:
    findings = list_findings(db, status_, project_id, rule_id, limit, offset)
    return [_to_out(f) for f in findings]


@router.get("/findings/{finding_id}", response_model=FindingOut)
def get_finding(finding_id: str, db: Session = Depends(get_tenant_db)) -> FindingOut:
    from app.models.findings import Finding

    target = db.get(Finding, finding_id)  # RLS garante que é do tenant atual
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "achado não encontrado")
    return _to_out(target, get_evidence(db, finding_id))


@router.post("/findings/{finding_id}/review", response_model=FindingOut)
def post_review(
    finding_id: str,
    body: ReviewIn,
    db: Session = Depends(get_tenant_db),
    user: CurrentUser = Depends(
        require_role(Role.OWNER.value, Role.CONTROLLER.value, Role.TENANT_ADMIN.value)
    ),
) -> FindingOut:
    try:
        finding = review_finding(db, user.tenant_id, finding_id, body.decision, user.email, body.reason)
    except DomainError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    return _to_out(finding, get_evidence(db, finding_id))
