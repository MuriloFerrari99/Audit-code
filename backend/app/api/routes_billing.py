"""Rotas de cobrança (Fase 2). Ver docs/fase-2-monetizacao.md."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_tenant_db
from app.billing.service import billing_summary

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/me")
def my_billing(db: Session = Depends(get_tenant_db)) -> dict:
    """Plano, uso do período e fatura projetada (base + excedente por nota)."""
    return billing_summary(db)
