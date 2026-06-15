"""Rotas de cobrança (Fase 2). Ver docs/fase-2-monetizacao.md."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_role
from app.billing.providers import get_provider
from app.billing.service import (
    apply_provider_event,
    billing_summary,
    get_statement,
    issue_statement,
)
from app.core.logging import get_logger
from app.models.auth import Role
from app.models.billing import Plan

router = APIRouter(prefix="/billing", tags=["billing"])
log = get_logger("billing")


@router.get("/me")
def my_billing(db: Session = Depends(get_tenant_db)) -> dict:
    """Plano, uso do período e fatura projetada (base + excedente por nota)."""
    return billing_summary(db)


@router.get("/statement")
def statement(period: str | None = None, db: Session = Depends(get_tenant_db)) -> dict:
    """Extrato do período: mensalidade + gainshare (economia validada elegível)."""
    return get_statement(db, period)


@router.post("/statement/close")
def close_statement(
    period: str | None = None,
    db: Session = Depends(get_tenant_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Materializa o extrato como billing_event (trilha de auditoria). Restrito."""
    require_role(Role.OWNER.value, Role.TENANT_ADMIN.value, Role.CONTROLLER.value)(user)
    return issue_statement(db, user.tenant_id, period)


@router.post("/checkout")
def checkout(
    plan_code: str,
    db: Session = Depends(get_tenant_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Cria a sessão de checkout do provedor p/ assinar um plano. Exige provedor
    configurado e Price cadastrado (plan.features.stripe_price_id)."""
    provider = get_provider()
    if provider is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "cobrança não configurada")
    plan = db.execute(select(Plan).where(Plan.code == plan_code)).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "plano inexistente")
    price_ref = (plan.features or {}).get("stripe_price_id")
    if not price_ref:
        raise HTTPException(status.HTTP_409_CONFLICT, "plano sem price do provedor")
    base = os.environ.get("APP_PUBLIC_URL", "http://localhost:3000")
    return provider.create_checkout(
        tenant_id=user.tenant_id, plan_code=plan_code, price_ref=price_ref,
        success_url=f"{base}/billing?ok=1", cancel_url=f"{base}/billing?cancel=1",
        customer_ref=None,
    )


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict:
    """Webhook do provedor. NÃO autenticado por token — verificado por ASSINATURA.
    Atualiza o estado da assinatura (ativa/past_due/cancelada)."""
    provider = get_provider()
    if provider is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "cobrança não configurada")
    payload = await request.body()
    try:
        event = provider.parse_event(payload, stripe_signature)
    except Exception as e:  # assinatura inválida / payload malformado
        log.warning("billing.webhook.invalid", error=str(e))
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "webhook inválido") from e
    result = apply_provider_event(event)
    log.info("billing.webhook.ok", type=event.type, handled=result["handled"])
    return {"ok": True, **result}
