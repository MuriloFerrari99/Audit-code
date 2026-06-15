"""Fase Agêntica P2 — ReferencePriceProvider BR/SINAPI injetado no Enriquecedor."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.adapters.references import BrazilSinapiProvider
from app.agents.squad import EnricherAgent, SquadContext
from app.canonical.document import (
    CanonicalDocument,
    CanonicalItem,
    DocumentType,
    SourceFormat,
)
from app.core.db import tenant_session
from app.models.agentic import AgentReasoningLog
from app.models.catalog import SinapiReference
from scripts.seed_synthetic import TENANT_ID, seed

SINAPI_CODE = "74209/001"


@pytest.fixture
def seeded():
    seed()
    with tenant_session(str(TENANT_ID)) as s:
        s.query(SinapiReference).filter(SinapiReference.sinapi_code == SINAPI_CODE).delete()
        s.add(SinapiReference(sinapi_code=SINAPI_CODE, state="SP", period="2026-05",
                              price=Decimal("28.50"), regime="desonerado"))


def _doc() -> CanonicalDocument:
    return CanonicalDocument(
        source_format=SourceFormat.NFE, document_type=DocumentType.GOODS_INVOICE,
        external_id="doc-1",
        items=[CanonicalItem(description="Cimento", code=SINAPI_CODE, unit_price=Decimal("40"))],
    )


def test_provider_resolves_sinapi(seeded):
    with tenant_session(str(TENANT_ID)) as s:
        ref = BrazilSinapiProvider(s, state="SP").resolve(
            code=SINAPI_CODE, description="Cimento", country="BR", industry="construction"
        )
    assert ref is not None
    assert ref.unit_price == Decimal("28.5000")
    assert ref.source == "SINAPI"
    assert ref.layer == "camada_1_sinapi"


def test_provider_ignores_other_country(seeded):
    with tenant_session(str(TENANT_ID)) as s:
        ref = BrazilSinapiProvider(s, state="SP").resolve(
            code=SINAPI_CODE, description="x", country="US", industry="construction"
        )
    assert ref is None


def test_enricher_uses_provider(seeded):
    ctx = SquadContext(tenant_id=str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        provider = BrazilSinapiProvider(s, state="SP")
        refs = EnricherAgent(provider).enrich(s, ctx, _doc())
        assert SINAPI_CODE in refs
        assert refs[SINAPI_CODE].unit_price == Decimal("28.5000")
    with tenant_session(str(TENANT_ID)) as s:
        log = s.execute(
            AgentReasoningLog.__table__.select().where(
                AgentReasoningLog.run_id == ctx.run_id
            )
        ).first()
    assert log is not None
    assert log.agent_name == "enricher"
    assert log.status == "ok"


def test_enricher_without_provider_skips(seeded):
    ctx = SquadContext(tenant_id=str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        refs = EnricherAgent(None).enrich(s, ctx, _doc())
        assert refs == {}
    with tenant_session(str(TENANT_ID)) as s:
        log = s.execute(
            AgentReasoningLog.__table__.select().where(AgentReasoningLog.run_id == ctx.run_id)
        ).first()
    assert log.status == "skipped"