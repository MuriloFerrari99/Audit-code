"""Teste do conector Sienge sem credencial (ADR-13, T-066).

Exercita pull (fixtures) + normalize. Não precisa de Postgres nem de API real.
"""

from __future__ import annotations

from app.connectors.base import EntityKind, PullCursor
from app.connectors.sienge.connector import SiengeConnector
from app.core.secrets import EnvSecretProvider


def _connector() -> SiengeConnector:
    # Sem segredos -> modo fixtures automático.
    return SiengeConnector("test-tenant", EnvSecretProvider(), use_fixtures=True)


def test_pull_fixtures_purchase_orders():
    c = _connector()
    rows = list(c.pull(EntityKind.PURCHASE_ORDER, PullCursor()))
    assert len(rows) == 2
    assert rows[0].source_external_id == "90001"


def test_normalize_purchase_order():
    c = _connector()
    raw = next(iter(c.pull(EntityKind.PURCHASE_ORDER, PullCursor())))
    rec = c.normalize(raw)
    assert rec.fields["tenant_id"] == "test-tenant"
    assert rec.fields["source"] == "sienge"
    assert str(rec.fields["total"]) == "4000.0"
    assert rec.fields["source_external_id"] == "90001"


def test_health_fixtures_ok():
    assert _connector().health().ok is True
