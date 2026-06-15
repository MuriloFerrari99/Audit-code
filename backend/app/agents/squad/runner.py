"""Orquestrador do OpenSquad — pipeline por documento (unidade de trabalho).

Encadeia Extrator -> Enriquecedor -> Auditor numa execução com `run_id` único.
Reaproveita a carga existente (persistência canônica + metering + dead-letter) e
acrescenta o prontuário de raciocínio. É o que um worker event-driven chama por
documento da fila de uploads do tenant; nunca falha em silêncio.
"""

from __future__ import annotations

import contextlib
import uuid

from app.adapters.references import BrazilSinapiProvider
from app.agents.squad.auditor import AuditorAgent
from app.agents.squad.base import AgentResult, SquadContext
from app.agents.squad.enricher import EnricherAgent
from app.agents.squad.extractor import ExtractorAgent
from app.connectors.upload.load import load_nfe_files
from app.core.db import tenant_session
from app.core.logging import get_logger
from app.models.platform import DeadLetter
from app.models.tenancy import Tenant

log = get_logger("squad.runner")


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


def _context(session, tenant_id: str) -> SquadContext:
    t = session.get(Tenant, uuid.UUID(tenant_id))
    return SquadContext(
        tenant_id=tenant_id,
        country=t.country_code if t else "BR",
        industry=getattr(t, "industry", "construction") if t else "construction",
        locale="pt-BR" if (t is None or t.country_code == "BR") else "en-US",
    )


class SquadRunner:
    """Pipeline por documento. enable_enricher liga a referência de preço."""

    def __init__(self, *, enable_enricher: bool = True) -> None:
        self.enable_enricher = enable_enricher

    def run_document(self, tenant_id: str, filename: str, content: bytes) -> dict:
        _register_rules()
        # 1) persiste no canônico (parse + Invoice/itens + metering + dead-letter)
        load = load_nfe_files(tenant_id, [(filename, content)])
        if load.get("invoices", 0) == 0 and load.get("dead_letters", 0) > 0:
            # documento inválido já foi para dead_letter na carga; não roda o squad
            log.info("squad.run.skipped_invalid", tenant_id=tenant_id, ref=filename)
            return {"run_id": None, "extracted": False, "found": {},
                    "dead_letters": load["dead_letters"]}

        with tenant_session(tenant_id) as s:
            ctx = _context(s, tenant_id)
            try:
                doc = ExtractorAgent().extract(s, ctx, filename, content)
                provider = (
                    BrazilSinapiProvider(s)
                    if self.enable_enricher and ctx.country == "BR" and ctx.industry == "construction"
                    else None
                )
                EnricherAgent(provider).enrich(s, ctx, doc)
                found = AuditorAgent().audit(s, ctx)
            except Exception as e:  # nunca falha em silêncio
                s.rollback()
                with tenant_session(tenant_id) as s2:
                    s2.add(DeadLetter(tenant_id=tenant_id, source="squad",
                                      entity_type="document", ref=filename,
                                      reason=f"squad: {e}"[:500]))
                log.warning("squad.run.failed", tenant_id=tenant_id, ref=filename, error=str(e))
                return {"run_id": str(ctx.run_id), "extracted": False, "found": {},
                        "dead_letters": load.get("dead_letters", 0) + 1}

            log.info("squad.run.ok", tenant_id=tenant_id, run_id=str(ctx.run_id),
                     found=sum(found.values()) if found else 0)
            return {"run_id": str(ctx.run_id), "extracted": True,
                    "source_format": doc.source_format.value, "found": found,
                    "dead_letters": load.get("dead_letters", 0)}


__all__ = ["SquadRunner", "AgentResult"]
