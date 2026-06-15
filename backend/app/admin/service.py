"""Serviço do painel admin (plataforma) — visão CROSS-TENANT.

Usa admin_session (role dono) DE PROPÓSITO: é operação de plataforma sobre
billing/tenancy, não leitura de dado de cliente. Gated por is_superuser na rota.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.billing.service import current_period, invoice_math
from app.core.db import admin_session
from app.models.billing import Plan, Subscription, UsageCounter
from app.models.tenancy import Tenant


def list_plans() -> list[dict]:
    with admin_session() as s:
        plans = s.execute(select(Plan).order_by(Plan.invoice_limit.asc())).scalars().all()
        return [
            {
                "code": p.code, "name": p.name, "base_price": str(p.base_price),
                "invoice_limit": p.invoice_limit, "overage_price": str(p.overage_price),
                "gainshare_pct": str(p.gainshare_pct) if p.gainshare_pct is not None else None,
                "active": p.active,
            }
            for p in plans
        ]


def tenants_overview(period: str | None = None) -> dict:
    p = period or current_period()
    with admin_session() as s:
        tenants = s.execute(select(Tenant).order_by(Tenant.created_at.asc())).scalars().all()
        rows = []
        for t in tenants:
            sub = s.execute(
                select(Subscription)
                .where(Subscription.tenant_id == t.id, Subscription.status != "canceled")
                .order_by(Subscription.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            plan = s.get(Plan, sub.plan_id) if sub else None
            uc = s.execute(
                select(UsageCounter).where(
                    UsageCounter.tenant_id == t.id, UsageCounter.period == p
                )
            ).scalar_one_or_none()
            used = uc.invoices_count if uc else 0
            inv = invoice_math(plan, used, p)
            rows.append({
                "tenant_id": str(t.id),
                "name": t.name,
                "status": t.status,
                "plan_code": plan.code if plan else None,
                "subscription_status": sub.status if sub else "none",
                "invoices_used": used,
                "invoice_limit": inv["invoice_limit"],
                "total": inv["total"],
            })
        return {"period": p, "tenants": rows}


def set_tenant_plan(tenant_id: str, plan_code: str) -> dict:
    """Atribui/troca o plano do tenant (override administrativo). Idempotente."""
    tid = uuid.UUID(str(tenant_id))
    with admin_session() as s:
        plan = s.execute(select(Plan).where(Plan.code == plan_code)).scalar_one_or_none()
        if plan is None:
            raise ValueError("plano inexistente")
        sub = s.execute(
            select(Subscription)
            .where(Subscription.tenant_id == tid)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if sub is None:
            sub = Subscription(tenant_id=tid, plan_id=plan.id, status="active")
            s.add(sub)
        else:
            sub.plan_id = plan.id
            if sub.status in ("none", "incomplete", "canceled"):
                sub.status = "active"
        return {"tenant_id": str(tid), "plan_code": plan.code, "status": sub.status}
