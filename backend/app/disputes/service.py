"""Serviço de mitigação (Agente Executor). Respeita o opt-in por tenant.

Sem `auto_mitigation`: abre a disputa como rascunho (sem efeito externo). Com
opt-in: usa os adapters configurados (default log-only) para agir e registra o
resultado. Idempotente por achado (ver ExecutorAgent.open_dispute).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.erp import get_erp_adapter
from app.adapters.notification import get_notifier
from app.agents.squad.base import SquadContext
from app.agents.squad.executor import ExecutorAgent
from app.models.agentic import Dispute
from app.models.tenancy import Tenant


def _context(session: Session, tenant_id: str) -> SquadContext:
    t = session.get(Tenant, uuid.UUID(tenant_id))
    return SquadContext(
        tenant_id=tenant_id,
        country=t.country_code if t else "BR",
        industry=getattr(t, "industry", "construction") if t else "construction",
        locale="pt-BR" if (t is None or t.country_code == "BR") else "en-US",
    )


def mitigate_finding(session: Session, tenant_id: str, *, finding_id: str, reason: str,
                     channel: str = "draft", bill_external_id: str | None = None,
                     recipient: str | None = None) -> Dispute:
    """Abre/!executa a mitigação de um achado conforme o opt-in do tenant."""
    t = session.get(Tenant, uuid.UUID(tenant_id))
    auto = bool(getattr(t, "auto_mitigation", False))
    ctx = _context(session, tenant_id)

    erp = notifier = None
    if auto and channel == "erp":
        erp = get_erp_adapter(tenant_id)
    elif auto and channel == "email":
        notifier = get_notifier(tenant_id)
    # auto desligado OU channel=draft -> nenhum adapter -> disputa fica em rascunho

    return ExecutorAgent(erp=erp, notifier=notifier).open_dispute(
        session, ctx, finding_id=finding_id, reason=reason,
        bill_external_id=bill_external_id, recipient=recipient,
    )


def list_disputes(session: Session, limit: int = 200) -> list[Dispute]:
    return list(
        session.execute(
            select(Dispute).order_by(Dispute.created_at.desc()).limit(limit)
        ).scalars()
    )
