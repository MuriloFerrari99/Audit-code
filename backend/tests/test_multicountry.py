"""Fase Agêntica P6 — seleção de provider por país (hexágono multi-país).

Prova que acoplar outro país é só um adapter: o factory escolhe BR/SINAPI ou
US/RSMeans sem o Core/Enricher/Runner mudarem.
"""

from __future__ import annotations

from app.adapters.references import (
    BrazilSinapiProvider,
    RSMeansProvider,
    get_reference_provider,
)
from app.core.db import tenant_session
from scripts.seed_synthetic import TENANT_ID, seed


def test_factory_selects_by_country():
    seed()
    with tenant_session(str(TENANT_ID)) as s:
        assert isinstance(get_reference_provider(s, "BR", "construction"), BrazilSinapiProvider)
        assert isinstance(get_reference_provider(s, "US", "construction"), RSMeansProvider)
        assert get_reference_provider(s, "BR", "healthcare") is None  # setor sem adapter
        assert get_reference_provider(s, "FR", "construction") is None  # país sem adapter


def test_us_provider_resolves_none_for_now():
    seed()
    with tenant_session(str(TENANT_ID)) as s:
        ref = RSMeansProvider(s).resolve(
            code="X", description="concrete", country="US", industry="construction"
        )
    assert ref is None  # base US ainda não ingerida — sem falso lastro
