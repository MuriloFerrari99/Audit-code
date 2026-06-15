"""Agente Extrator — bytes brutos -> CDM (via Adapter correto)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.squad.base import AgentResult, SquadAgent, SquadContext
from app.canonical.document import CanonicalDocument, SourceFormat
from app.canonical.mappers import fiscal_dict_to_canonical
from app.connectors.upload.nfe import parse_nfe
from app.connectors.upload.nfse import looks_like_nfse, parse_nfse


class ExtractorAgent(SquadAgent):
    """Identifica o tipo de arquivo e roda o adapter -> documento canônico."""

    name = "extractor"

    def extract(self, session: Session, ctx: SquadContext,
                filename: str, content: bytes) -> CanonicalDocument:
        if looks_like_nfse(content):
            doc = fiscal_dict_to_canonical(parse_nfse(content), SourceFormat.NFSE)
        else:
            doc = fiscal_dict_to_canonical(parse_nfe(content), SourceFormat.NFE)
        self.log(
            session, ctx,
            AgentResult(
                agent_name=self.name,
                confidence=1.0,
                reasoning=f"Arquivo {filename} reconhecido como {doc.source_format.value}; "
                          f"{len(doc.items)} item(ns); total {doc.total_amount}.",
            ),
            document_external_id=doc.external_id or filename,
        )
        return doc
