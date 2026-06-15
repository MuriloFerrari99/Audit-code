"""Serviço de cobrança (Fase 2): medição de uso e cálculo da fatura mensal.

A fatura é calculada do USO REAL de uploads do tenant:
    total = base_price + max(0, notas_usadas - invoice_limit) * overage_price

Tudo tenant-scoped (RLS). O incremento de uso é idempotente por período e
chamado na carga de notas (connectors/upload/load.py).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.db import admin_session
from app.core.timeutils import now_utc, period_key
from app.models.billing import BillingEvent, Plan, Subscription, UsageCounter
from app.models.findings import Finding, ValueLedger

D = Decimal

# Regras elegíveis a gainshare (gtm.md): só hard savings + cost avoidance, com
# baseline e evidência. Governança (R3 fracionamento, R6 sem concorrência),
# integridade (I*) e flags fiscais/retenção (F2/RET*) NÃO entram na fatura —
# são valor demonstrado, não faturado. Whitelist explícita (mais seguro).
GAINSHARE_ELIGIBLE_RULES = frozenset({"R1", "R2", "R4", "R5", "F1", "F3", "P1", "P2"})


def current_period() -> str:
    """Período mensal corrente (AAAA-MM) na tz de negócio."""
    return period_key(now_utc())


def increment_usage(session: Session, tenant_id: str, *, invoices: int = 0, findings: int = 0,
                    period: str | None = None) -> None:
    """Soma uso no contador do período (upsert atômico por (tenant, período))."""
    if invoices == 0 and findings == 0:
        return
    p = period or current_period()
    stmt = pg_insert(UsageCounter).values(
        tenant_id=tenant_id, period=p, invoices_count=invoices, findings_count=findings,
    ).on_conflict_do_update(
        constraint="uq_usage_tenant_period",
        set_={
            "invoices_count": UsageCounter.invoices_count + invoices,
            "findings_count": UsageCounter.findings_count + findings,
            "updated_marker": now_utc(),
        },
    )
    session.execute(stmt)


def _active_subscription(session: Session) -> Subscription | None:
    return session.execute(
        select(Subscription).where(Subscription.status == "active").limit(1)
    ).scalar_one_or_none()


def _usage(session: Session, period: str) -> UsageCounter | None:
    return session.execute(
        select(UsageCounter).where(UsageCounter.period == period)
    ).scalar_one_or_none()


def compute_monthly_invoice(session: Session, period: str | None = None) -> dict:
    """Fatura do período: base + excedente por nota acima do limite do plano."""
    p = period or current_period()
    sub = _active_subscription(session)
    plan = session.get(Plan, sub.plan_id) if sub else None
    usage = _usage(session, p)
    used = usage.invoices_count if usage else 0

    if plan is None:
        return {
            "period": p, "plan": None, "invoices_used": used,
            "invoice_limit": None, "overage_units": 0,
            "base_price": "0", "overage_price": "0",
            "overage_amount": "0", "total": "0",
        }

    limit = int(plan.invoice_limit or 0)
    base = D(str(plan.base_price or 0))
    over_price = D(str(plan.overage_price or 0))
    over_units = max(0, used - limit)
    over_amount = over_price * over_units
    total = base + over_amount
    return {
        "period": p,
        "plan": {"code": plan.code, "name": plan.name},
        "invoices_used": used,
        "invoice_limit": limit,
        "overage_units": over_units,
        "base_price": str(base),
        "overage_price": str(over_price),
        "overage_amount": str(over_amount),
        "total": str(total),
    }


def billing_summary(session: Session) -> dict:
    """Resumo p/ o painel do cliente: plano, uso e fatura projetada do período."""
    sub = _active_subscription(session)
    invoice = compute_monthly_invoice(session)
    invoice["subscription_status"] = sub.status if sub else "none"
    return invoice


# ----------------------------------------------------------------- gainshare
def compute_gainshare(session: Session, period: str | None = None) -> dict:
    """Base de gainshare do período = Σ validated_amount de achados ACEITOS cujas
    regras sejam elegíveis (hard savings + cost avoidance). gtm.md."""
    p = period or current_period()
    rows = session.execute(
        select(Finding.rule_id, func.coalesce(func.sum(ValueLedger.validated_amount), 0))
        .join(Finding, Finding.id == ValueLedger.finding_id)
        .where(
            ValueLedger.period == p,
            ValueLedger.status == "validated",
            Finding.rule_id.in_(GAINSHARE_ELIGIBLE_RULES),
        )
        .group_by(Finding.rule_id)
    ).all()
    by_rule = {rid: str(D(str(amt))) for rid, amt in rows}
    base = sum((D(str(amt)) for _, amt in rows), D(0))

    sub = _active_subscription(session)
    plan = session.get(Plan, sub.plan_id) if sub else None
    pct = D(str(plan.gainshare_pct)) if plan and plan.gainshare_pct is not None else None
    amount = (base * pct) if pct is not None else None
    return {
        "period": p,
        "base": str(base),
        "by_rule": by_rule,
        "gainshare_pct": str(pct) if pct is not None else None,
        "gainshare_amount": str(amount) if amount is not None else None,
        "eligible_rules": sorted(GAINSHARE_ELIGIBLE_RULES),
    }


def get_statement(session: Session, period: str | None = None) -> dict:
    """Extrato do período: mensalidade (base+excedente) + gainshare."""
    p = period or current_period()
    return {
        "period": p,
        "monthly": compute_monthly_invoice(session, p),
        "gainshare": compute_gainshare(session, p),
    }


def _upsert_billing_event(session: Session, tenant_id: str, period: str, kind: str,
                          amount: Decimal, detail: dict) -> None:
    stmt = pg_insert(BillingEvent).values(
        tenant_id=tenant_id, period=period, kind=kind, amount=amount,
        status="issued", detail=detail,
    ).on_conflict_do_update(
        constraint="uq_billing_tenant_period_kind",
        set_={"amount": amount, "detail": detail, "status": "issued"},
    )
    session.execute(stmt)


def issue_statement(session: Session, tenant_id: str, period: str | None = None) -> dict:
    """Materializa o extrato do período como billing_event (idempotente por
    (tenant, período, kind)). Trilha de auditoria da cobrança."""
    st = get_statement(session, period)
    p = st["period"]
    _upsert_billing_event(session, tenant_id, p, "base",
                          D(st["monthly"]["total"]), st["monthly"])
    gs = st["gainshare"]["gainshare_amount"]
    _upsert_billing_event(session, tenant_id, p, "gainshare",
                          D(gs) if gs is not None else D(0), st["gainshare"])
    return st


# ----------------------------------------------------------------- provedor (webhook)
def apply_provider_event(event) -> dict:
    """Aplica um evento de webhook (já verificado) ao schema. Operação de
    PLATAFORMA (admin_session): vincula/atualiza a assinatura por provider_ref.
    Idempotente — reaplicar o mesmo evento converge ao mesmo estado."""
    with admin_session() as s:
        sub = None
        if event.type == "checkout.session.completed" and event.tenant_id:
            sub = s.execute(
                select(Subscription)
                .where(Subscription.tenant_id == uuid.UUID(str(event.tenant_id)))
                .order_by(Subscription.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            if sub is not None:
                sub.provider = "stripe"
                sub.provider_ref = event.subscription_ref
                sub.status = "active"
        elif event.subscription_ref:
            sub = s.execute(
                select(Subscription).where(Subscription.provider_ref == event.subscription_ref)
            ).scalar_one_or_none()
            if sub is not None and event.status:
                sub.status = event.status
        return {"handled": sub is not None, "type": event.type}
