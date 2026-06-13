"""Casamento de insumo -> catálogo canônico (T-083, ml.md Job 1).

Cascata: normalização determinística -> embedding -> similaridade (pgvector).
Acima do limiar alto = auto; faixa intermediária = ambíguo (fila humana / agente
Casador); abaixo = sem match. A decisão humana vira item_mapping (rótulo).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.embeddings import EmbeddingProvider
from app.ml.normalize import normalize_description
from app.models.catalog import CatalogItem

AUTO_THRESHOLD = 0.85
AMBIGUOUS_THRESHOLD = 0.60


@dataclass
class MatchResult:
    catalog_item_id: str | None
    confidence: float
    status: str  # auto | ambiguous | none


def match_description(
    session: Session, raw_description: str, provider: EmbeddingProvider
) -> MatchResult:
    normalized = normalize_description(raw_description)
    vec = provider.embed(normalized)

    row = session.execute(
        select(
            CatalogItem.id,
            CatalogItem.embedding.cosine_distance(vec).label("distance"),
        )
        .where(CatalogItem.embedding.is_not(None))
        .order_by("distance")
        .limit(1)
    ).first()

    if row is None:
        return MatchResult(None, 0.0, "none")

    catalog_id, distance = row
    confidence = max(0.0, 1.0 - float(distance))  # cosine distance -> similaridade
    if confidence >= AUTO_THRESHOLD:
        return MatchResult(str(catalog_id), confidence, "auto")
    if confidence >= AMBIGUOUS_THRESHOLD:
        return MatchResult(str(catalog_id), confidence, "ambiguous")
    return MatchResult(None, confidence, "none")
