"""Rotas do painel admin (plataforma, cross-tenant). Gated por is_superuser."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.admin.service import list_plans, set_tenant_plan, tenants_overview
from app.api.deps import CurrentUser, require_platform_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/plans")
def admin_plans(_: CurrentUser = Depends(require_platform_admin)) -> dict:
    return {"plans": list_plans()}


@router.get("/tenants")
def admin_tenants(
    period: str | None = None,
    _: CurrentUser = Depends(require_platform_admin),
) -> dict:
    """Visão de todos os tenants: plano, uso do período e fatura projetada."""
    return tenants_overview(period)


@router.post("/tenants/{tenant_id}/plan")
def admin_set_plan(
    tenant_id: str,
    plan_code: str,
    _: CurrentUser = Depends(require_platform_admin),
) -> dict:
    """Override administrativo do plano do tenant."""
    try:
        return set_tenant_plan(tenant_id, plan_code)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e)) from e
