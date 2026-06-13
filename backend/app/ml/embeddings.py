"""Provedor de embeddings (T-082, ADR-12).

Interface + dois provedores:
- ExternalEmbeddingProvider: chama a API externa (chave via SecretProvider) — a
  definir (A6); placeholder com o ponto de integração.
- DeterministicStubProvider: vetor pseudo-determinístico a partir de hash, para
  dev/teste rodarem o casamento por pgvector SEM chave externa.

Embeddings de descrição (texto de insumo, sem PII) são cacheados por hash.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol

from app.models.catalog import EMBEDDING_DIM


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]: ...


class DeterministicStubProvider:
    """Gera um vetor estável e normalizado a partir do hash do texto.

    Não tem semântica real (não substitui embedding de verdade), mas permite
    exercitar o pipeline pgvector ponta a ponta sem custo/credencial.
    """

    def __init__(self, dim: int = EMBEDDING_DIM):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        seed = hashlib.sha256(text.encode()).digest()
        vals: list[float] = []
        i = 0
        while len(vals) < self.dim:
            h = hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
            for b in h:
                vals.append((b / 255.0) * 2 - 1)
                if len(vals) >= self.dim:
                    break
            i += 1
        norm = math.sqrt(sum(v * v for v in vals)) or 1.0
        return [v / norm for v in vals]


class ExternalEmbeddingProvider:
    """Chama a API externa de embeddings. A definir (A6 — provider/modelo)."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def embed(self, text: str) -> list[float]:  # pragma: no cover - depende de chave externa
        raise NotImplementedError(
            "Integração com o provedor externo de embeddings entra quando A6 for definido."
        )


def get_embedding_provider(api_key: str | None, model: str | None) -> EmbeddingProvider:
    if api_key and model:
        return ExternalEmbeddingProvider(api_key, model)
    return DeterministicStubProvider()
