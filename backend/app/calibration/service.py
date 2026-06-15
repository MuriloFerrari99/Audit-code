"""Calibração por (tenant, regra) a partir dos rótulos humanos (Módulo C).

Estatística honesta (não DL): taxa de aceite -> confidence_factor que o engine
multiplica na confiança-base. Mínimo de amostras antes de calibrar. Sugestões de
threshold/desligar são para APROVAÇÃO humana (nunca automáticas).
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.findings import Finding, FindingReview, RuleCalibration

log = get_logger("calibration")

MIN_SAMPLES = 10
HIGH_DISMISS = 0.70
HIGH_ACCEPT = 0.85


def factor_for(acceptance_rate: float | None, samples: int) -> float:
    """Fator de confiança ∈ [0.5, 1.1]. Sem amostra suficiente -> 1.0 (neutro)."""
    if samples < MIN_SAMPLES or acceptance_rate is None:
        return 1.0
    return round(max(0.5, min(1.1, 0.6 + 0.5 * acceptance_rate)), 3)


def _suggest(rule_id: str, samples: int, accept_rate: float) -> str | None:
    if samples < MIN_SAMPLES:
        return None
    if accept_rate <= 1 - HIGH_DISMISS:
        return (
            f"{rule_id}: {round((1 - accept_rate) * 100)}% descartados em {samples} revisões — "
            f"reveja o threshold ou considere desligar esta regra para este cliente."
        )
    if accept_rate >= HIGH_ACCEPT:
        return (
            f"{rule_id}: {round(accept_rate * 100)}% aceitos — regra confiável para este cliente."
        )
    return None


def recompute(session: Session, tenant_id: str) -> dict:
    """Recalcula a calibração da base de reviews e faz upsert. Retorna stats+sugestões."""
    rows = session.execute(
        select(Finding.rule_id, FindingReview.decision, func.count())
        .join(FindingReview, FindingReview.finding_id == Finding.id)
        .group_by(Finding.rule_id, FindingReview.decision)
    ).all()
    agg: dict[str, dict[str, int]] = {}
    for rule_id, decision, n in rows:
        d = agg.setdefault(rule_id, {"accept": 0, "dismiss": 0, "escalate": 0})
        if decision in d:
            d[decision] += n

    stats, suggestions = [], []
    for rule_id, d in agg.items():
        accepted = d["accept"] + d["escalate"]  # escalar = leva a sério
        dismissed = d["dismiss"]
        samples = accepted + dismissed
        rate = (accepted / samples) if samples else None
        factor = factor_for(rate, samples)

        cal = session.execute(
            select(RuleCalibration).where(RuleCalibration.rule_id == rule_id)
        ).scalar_one_or_none()
        if cal is None:
            cal = RuleCalibration(tenant_id=tenant_id, rule_id=rule_id)
            session.add(cal)
        cal.samples = samples
        cal.accepted = accepted
        cal.dismissed = dismissed
        cal.acceptance_rate = rate
        cal.confidence_factor = factor

        stats.append(
            {
                "rule_id": rule_id,
                "samples": samples,
                "accepted": accepted,
                "dismissed": dismissed,
                "acceptance_rate": rate,
                "confidence_factor": factor,
            }
        )
        s = _suggest(rule_id, samples, rate if rate is not None else 0.0)
        if s:
            suggestions.append(s)
    log.info("calibration.recompute", tenant_id=tenant_id, rules=len(stats))
    return {"stats": stats, "suggestions": suggestions}


def get_calibration(session: Session) -> dict:
    """Leitura (read-only) da calibração atual + sugestões derivadas."""
    rows = session.execute(select(RuleCalibration)).scalars().all()
    stats, suggestions = [], []
    for c in rows:
        rate = float(c.acceptance_rate) if c.acceptance_rate is not None else None
        stats.append(
            {
                "rule_id": c.rule_id,
                "samples": c.samples,
                "accepted": c.accepted,
                "dismissed": c.dismissed,
                "acceptance_rate": rate,
                "confidence_factor": float(c.confidence_factor),
            }
        )
        s = _suggest(c.rule_id, c.samples, rate if rate is not None else 0.0)
        if s:
            suggestions.append(s)
    return {"stats": stats, "suggestions": suggestions}


def get_factors(session: Session) -> dict[str, float]:
    """Fatores de confiança por regra para o tenant atual (RLS). Default vazio."""
    rows = session.execute(select(RuleCalibration.rule_id, RuleCalibration.confidence_factor)).all()
    return {rid: float(f) for rid, f in rows}
