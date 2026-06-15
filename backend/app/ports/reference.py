"""Port de saída: preço de referência de mercado (SINAPI BR, RSMeans US...)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class PriceReference:
    """Referência de preço resolvida p/ um item (com proveniência)."""

    unit_price: Decimal
    source: str          # ex.: sinapi, internal_median, rsmeans
    layer: str | None = None
    sample_size: int | None = None


@runtime_checkable
class ReferencePriceProvider(Protocol):
    """Fonte de preço de mercado, selecionada por país/setor do tenant."""

    def resolve(self, *, code: str | None, description: str, country: str,
                industry: str) -> PriceReference | None:
        """Devolve a referência de preço, ou None se não houver lastro confiável."""
        ...
