"""Rotas de relatório/resumo executivo (Narrador) e dossiê (Investigador)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.investigator import build_dossier
from app.agents.llm import LLMClient
from app.agents.narrador import monthly_summary
from app.api.deps import CurrentUser, get_current_user, get_tenant_db
from app.core.secrets import get_secret_provider
from app.core.timeutils import now_utc, period_key

router = APIRouter(tags=["reports"])


def _llm() -> LLMClient:
    return LLMClient(get_secret_provider())


@router.get("/reports/monthly")
def report_monthly(
    period: str | None = None,
    db: Session = Depends(get_tenant_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    period = period or period_key(now_utc())
    return monthly_summary(db, user.tenant_id, period, llm=_llm())


@router.get("/findings/{finding_id}/dossier")
def finding_dossier(
    finding_id: str,
    db: Session = Depends(get_tenant_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    return build_dossier(db, finding_id, llm=_llm())
