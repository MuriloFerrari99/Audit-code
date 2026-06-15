"""Rotas de cobrança (Fase 2). Ver docs/fase-2-monetizacao.md."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_role
from app.billing.service import billing_summary, get_statement, issue_statement
from app.models.auth import Role

router = APIRouter(prefix="/billing", tags=["billing"])


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
