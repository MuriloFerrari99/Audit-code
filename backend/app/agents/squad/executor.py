"""Agente Executor — mitigação automática (Dispute: bloqueio em ERP / e-mail).

Por padrão abre a disputa como 'draft' (sem efeito externo). Só age para fora se
uma Port (ErpActionPort/NotificationPort) for injetada — e ação externa é
deliberada, idempotente e auditada. É a virada de advisory -> ação.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.squad.base import AgentResult, SquadAgent, SquadContext
from app.core.timeutils import now_utc
from app.models.agentic import Dispute
from app.ports.erp import ErpActionPort
from app.ports.notification import NotificationPort


class ExecutorAgent(SquadAgent):
    name = "executor"

    def __init__(self, erp: ErpActionPort | None = None,
                 notifier: NotificationPort | None = None) -> None:
        self.erp = erp
        self.notifier = notifier

    def open_dispute(self, session: Session, ctx: SquadContext, *, finding_id: str,
                     reason: str, bill_external_id: str | None = None,
                     recipient: str | None = None) -> Dispute:
        d = Dispute(
            tenant_id=ctx.tenant_id, finding_id=finding_id, status="draft",
            locale=ctx.locale, message=reason, recipient=recipient,
        )
        session.add(d)

        if self.erp is not None and bill_external_id:
            res = self.erp.block_payment(
                tenant_id=ctx.tenant_id, bill_external_id=bill_external_id, reason=reason,
            )
            d.channel = "erp"
            d.erp_action = "block_payment"
            d.erp_ref = res.external_ref
            d.status = "erp_blocked" if res.ok else "failed"
        elif self.notifier is not None and recipient:
            res = self.notifier.send_dispute(
                tenant_id=ctx.tenant_id, to=recipient,
                subject="Contestação de cobrança", body=reason, locale=ctx.locale,
            )
            d.channel = "email"
            d.status = "email_sent" if res.ok else "failed"
            d.sent_at = now_utc()
        session.flush()

        self.log(session, ctx, AgentResult(
            agent_name=self.name, confidence=0.95,
            reasoning=f"Disputa {d.status} (canal={d.channel or 'nenhum'}): {reason}",
        ), finding_id=finding_id)
        return d
