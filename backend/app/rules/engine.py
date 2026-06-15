"""Engine de regras (E10): persiste achados com dedup (ADR-03) e aplica o
ciclo de vida (ADR-02).

- Upsert por (tenant_id, dedup_key): re-run não duplica.
- Decisão humana é sticky: ACCEPTED/DISMISSED/ESCALATED nunca viram OPEN/RESOLVED
  automaticamente.
- Achado OPEN cuja condição deixou de valer -> RESOLVED.
- Achado RESOLVED/SUPERSEDED que volta a valer -> reaberto (OPEN).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calibration.service import get_factors
from app.core.logging import get_logger
from app.core.timeutils import now_utc
from app.models.findings import Finding, FindingEvidence, FindingStatus, RuleConfig
from app.rules.base import FindingDraft, Rule, RuleContext, registry
from app.rules.confidence import score as confidence_score

log = get_logger("rules")

HUMAN_DECIDED = {
    FindingStatus.ACCEPTED.value,
    FindingStatus.DISMISSED.value,
    FindingStatus.ESCALATED.value,
}


def resolve_config(session: Session, rule: Rule) -> tuple[dict, bool]:
    """Resolve params efetivos (default da regra <- override do tenant)."""
    params = dict(rule.default_params)
    row = session.execute(
        select(RuleConfig).where(RuleConfig.rule_id == rule.id)
    ).scalar_one_or_none()
    if row is None:
        return params, True
    if not row.enabled:
        return params, False
    params.update(row.params or {})
    return params, True


def _replace_evidence(
    session: Session, tenant_id: str, finding: Finding, draft: FindingDraft
) -> None:
    session.query(FindingEvidence).filter(FindingEvidence.finding_id == finding.id).delete()
    for ev in draft.evidence:
        session.add(
            FindingEvidence(
                tenant_id=tenant_id,
                finding_id=finding.id,
                entity_type=ev.entity_type,
                entity_id=ev.entity_id,
                role=ev.role,
                snippet=ev.snippet,
                value=ev.value,
            )
        )


def upsert_finding(
    session: Session, tenant_id: str, draft: FindingDraft, factors: dict[str, float] | None = None
) -> Finding:
    existing = session.execute(
        select(Finding).where(Finding.dedup_key == draft.dedup_key)
    ).scalar_one_or_none()
    amount = draft.exposed_amount.amount if draft.exposed_amount else None
    base = confidence_score(draft.rule_id, draft.reference_snapshot)
    factor = (factors or {}).get(draft.rule_id, 1.0)  # calibração por tenant (Módulo C)
    conf = round(max(0.0, min(1.0, base * factor)), 3)

    if existing is None:
        finding = Finding(
            tenant_id=tenant_id,
            project_id=draft.project_id,
            rule_id=draft.rule_id,
            rule_version=draft.rule_version,
            dedup_key=draft.dedup_key,
            severity=draft.severity,
            status=FindingStatus.OPEN.value,
            exposed_amount=amount,
            confidence=conf,
            reference_snapshot=draft.reference_snapshot,
            config_snapshot=draft.config_snapshot,
            title=draft.title,
        )
        session.add(finding)
        session.flush()
        _replace_evidence(session, tenant_id, finding, draft)
        return finding

    # Atualiza métricas sempre; status só se NÃO houver decisão humana.
    existing.exposed_amount = amount
    existing.confidence = conf
    existing.severity = draft.severity
    existing.title = draft.title
    existing.reference_snapshot = draft.reference_snapshot
    existing.config_snapshot = draft.config_snapshot
    if existing.status not in HUMAN_DECIDED:
        existing.status = FindingStatus.OPEN.value
        existing.resolved_at = None
        _replace_evidence(session, tenant_id, existing, draft)
    return existing


def resolve_stale(session: Session, rule_id: str, current_keys: set[str]) -> int:
    """OPEN que não disparou neste run -> RESOLVED (condição deixou de valer)."""
    open_findings = session.execute(
        select(Finding).where(
            Finding.rule_id == rule_id,
            Finding.status == FindingStatus.OPEN.value,
        )
    ).scalars()
    n = 0
    for f in open_findings:
        if f.dedup_key not in current_keys:
            f.status = FindingStatus.RESOLVED.value
            f.resolved_at = now_utc()
            n += 1
    return n


def run_rule(
    session: Session, ctx: RuleContext, rule: Rule, factors: dict[str, float] | None = None
) -> list[FindingDraft]:
    drafts = rule.evaluate(session, ctx)
    current_keys = {d.dedup_key for d in drafts}
    for d in drafts:
        upsert_finding(session, ctx.tenant_id, d, factors)
    resolved = resolve_stale(session, rule.id, current_keys)
    log.info("rule.run", rule=rule.id, found=len(drafts), resolved=resolved)
    return drafts


def run_all(session: Session, tenant_id: str, rule_ids: list[str] | None = None) -> dict[str, int]:
    factors = get_factors(session)  # calibração por tenant (Módulo C)
    summary: dict[str, int] = {}
    for rule in registry.all():
        if rule_ids and rule.id not in rule_ids:
            continue
        params, enabled = resolve_config(session, rule)
        if not enabled:
            continue
        ctx = RuleContext(tenant_id=tenant_id, params=params, now=now_utc())
        drafts = run_rule(session, ctx, rule, factors)
        summary[rule.id] = len(drafts)
    return summary
