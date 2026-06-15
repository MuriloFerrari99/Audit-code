"""Serviço de cobrança (Fase 2): medição de uso e cálculo da fatura mensal.

A fatura é calculada do USO REAL de uploads do tenant:
    total = base_price + max(0, notas_usadas - invoice_limit) * overage_price

Tudo tenant-scoped (RLS). O incremento de uso é idempotente por período e
chamado na carga de notas (connectors/upload/load.py).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.timeutils import now_utc, period_key
from app.models.billing import Plan, Subscription, UsageCounter

D = Decimal


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
