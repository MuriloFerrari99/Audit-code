"""Rotas de onboarding self-serve (docs/onboarding-ux.md)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.agents.llm import LLMClient
from app.agents.onboarding_agent import answer as assistant_answer
from app.api.deps import CurrentUser, get_current_user
from app.api.schemas import AssistantIn, SiengeCredsIn
from app.core.secrets import get_secret_provider
from app.onboarding.service import connect_sienge, get_status, probe_sienge, start_run

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/test")
def test_connection(body: SiengeCredsIn) -> dict:
    """Validação AO VIVO da credencial do Sienge (somente leitura). Aberta:
    testa o ERP do próprio usuário com a credencial que ele forneceu."""
    return probe_sienge(body.subdomain, body.user, body.password)


@router.post("/connect")
def connect(body: SiengeCredsIn, user: CurrentUser = Depends(get_current_user)) -> dict:
    return connect_sienge(user.tenant_id, body.subdomain, body.user, body.password)


@router.post("/run")
def run(user: CurrentUser = Depends(get_current_user)) -> dict:
    return start_run(user.tenant_id)


@router.get("/status")
def status(user: CurrentUser = Depends(get_current_user)) -> dict:
    return get_status(user.tenant_id)


@router.post("/assistant")
def assistant(body: AssistantIn) -> dict:
    """Agente de onboarding (fundamentado na base; não alucina)."""
    return assistant_answer(body.question, llm=LLMClient(get_secret_provider()))
