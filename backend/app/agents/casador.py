"""Agente Casador (agentes.md): resolve descrições ambíguas de insumo.

Usa a cascata de ml.matching; nos casos ambíguos pode acionar o LLM para
desambiguar com contexto. Não cria catalog_item — propõe; baixa confiança vai
para a fila humana (rótulo = item_mapping).
"""

from __future__ import annotations

from dataclasses import asdict

from sqlalchemy.orm import Session

from app.agents.llm import LLMClient
from app.ml.embeddings import EmbeddingProvider
from app.ml.matching import MatchResult, match_description


def suggest_match(
    session: Session,
    raw_description: str,
    provider: EmbeddingProvider,
    tenant_id: str,
    llm: LLMClient | None = None,
) -> dict:
    result: MatchResult = match_description(session, raw_description, provider)
    out = asdict(result)
    out["raw_description"] = raw_description
    if result.status == "ambiguous" and llm is not None:
        note = llm.complete(
            f"A descrição de insumo '{raw_description}' casou parcialmente (confiança "
            f"{result.confidence:.2f}). Confirme se é o mesmo insumo do catálogo candidato "
            f"e explique em uma frase. Responda 'sim'/'não' + justificativa.",
            tenant_id=tenant_id,
            task="cheap",
            max_tokens=200,
        )
        if note:
            out["llm_note"] = note
    return out
