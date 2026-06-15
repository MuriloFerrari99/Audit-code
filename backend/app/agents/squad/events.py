"""Disparo event-driven do squad: upload publica evento; worker drena e audita.

Desacopla a ingestão da auditoria (outbox pattern): a carga publica
`squad_audit` no outbox; um worker chama `drain_audit_outbox` por tenant, roda o
Auditor uma vez (colapsa eventos do ciclo) e marca os eventos como processados.
Idempotente e sem dependência de broker externo (drenável em teste).
"""

from __future__ import annotations

import contextlib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.squad.auditor import AuditorAgent
from app.agents.squad.base import SquadContext
from app.core.timeutils import now_utc
from app.models.platform import OutboxEvent
from app.models.tenancy import Tenant

AUDIT_EVENT = "squad_audit"


def publish_audit_request(session: Session, tenant_id: str) -> None:
    """Enfileira um pedido de auditoria para o tenant (chamado na carga)."""
    session.add(OutboxEvent(
        tenant_id=uuid.UUID(str(tenant_id)),
        entity_type=AUDIT_EVENT,
        entity_id=uuid.UUID(str(tenant_id)),
        change_type="requested",
    ))


def _register_rules() -> None:
    from app.rules.builtin import register_builtin_rules
    from app.rules.fiscal_rules import register_fiscal_rules
    from app.rules.integrity_rules import register_integrity_rules
    from app.rules.payment_rules import register_payment_rules
    from app.rules.retention_rules import register_retention_rules

    for reg in (register_builtin_rules, register_integrity_rules, register_fiscal_rules,
                register_payment_rules, register_retention_rules):
        with contextlib.suppress(ValueError):
            reg()


def drain_audit_outbox(session: Session, tenant_id: str, limit: int = 100) -> dict:
    """Processa eventos squad_audit pendentes do tenant: roda o Auditor 1x e
    marca todos como processados. Sem eventos -> no-op."""
    events = session.execute(
        select(OutboxEvent).where(
            OutboxEvent.entity_type == AUDIT_EVENT, OutboxEvent.processed_at.is_(None)
        ).limit(limit)
    ).scalars().all()
    if not events:
        return {"processed": 0, "found": {}}

    _register_rules()
    t = session.get(Tenant, uuid.UUID(str(tenant_id)))
    ctx = SquadContext(
        tenant_id=str(tenant_id),
        country=t.country_code if t else "BR",
        industry=getattr(t, "industry", "construction") if t else "construction",
    )
    found = AuditorAgent().audit(session, ctx)
    marker = now_utc()
    for e in events:
        e.processed_at = marker
    return {"processed": len(events), "found": found, "run_id": str(ctx.run_id)}
