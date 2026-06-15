"""Agente Auditor — roda as regras determinísticas e gera a trilha de auditoria.

Reaproveita o motor existente (app/rules/engine.run_all), que já aplica
classificação, guardas anti-falso-positivo, confiança e calibração por tenant.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.squad.base import AgentResult, SquadAgent, SquadContext
from app.rules.engine import run_all


class AuditorAgent(SquadAgent):
    name = "auditor"

    def audit(self, session: Session, ctx: SquadContext) -> dict:
        found = run_all(session, ctx.tenant_id)
        total = sum(found.values()) if isinstance(found, dict) else 0
        self.log(session, ctx, AgentResult(
            agent_name=self.name,
            confidence=0.9,
            reasoning=f"Motor de regras executado: {total} achado(s) por {len(found or {})} regra(s).",
            data={"by_rule": found},
        ))
        return found
