"""Agente Enriquecedor — anexa preço de referência aos itens do CDM.

Seleciona a fonte por país/setor do tenant via ReferencePriceProvider (Port).
Sem provedor injetado, registra o passo como 'skipped' (próximo passo do roadmap
liga o provedor BR/SINAPI reaproveitando app/rules/references.py).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.squad.base import AgentResult, SquadAgent, SquadContext
from app.canonical.document import CanonicalDocument
from app.ports.reference import PriceReference, ReferencePriceProvider


class EnricherAgent(SquadAgent):
    name = "enricher"

    def __init__(self, provider: ReferencePriceProvider | None = None) -> None:
        self.provider = provider

    def enrich(self, session: Session, ctx: SquadContext,
               doc: CanonicalDocument) -> dict[str, PriceReference]:
        refs: dict[str, PriceReference] = {}
        if self.provider is None:
            self.log(session, ctx, AgentResult(
                agent_name=self.name, status="skipped",
                reasoning="Sem provedor de referência configurado p/ "
                          f"{ctx.country}/{ctx.industry}.",
            ), document_external_id=doc.external_id)
            return refs
        for item in doc.items:
            ref = self.provider.resolve(
                code=item.code, description=item.description,
                country=ctx.country, industry=ctx.industry,
            )
            if ref is not None and item.code:
                refs[item.code] = ref
        self.log(session, ctx, AgentResult(
            agent_name=self.name, confidence=0.8,
            reasoning=f"{len(refs)}/{len(doc.items)} itens com referência de preço.",
        ), document_external_id=doc.external_id)
        return refs
