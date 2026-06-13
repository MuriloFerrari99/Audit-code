"""Fixtures de teste. Requer Postgres acessível (make up && make migrate)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.core.db import admin_session, db_healthy


@pytest.fixture(scope="session", autouse=True)
def _require_db():
    if not db_healthy():
        pytest.skip("Postgres indisponível — rode `make up && make migrate` antes dos testes")


@pytest.fixture
def two_tenants():
    """Cria dois tenants e devolve seus ids; limpa ao final."""
    a = uuid.uuid4()
    b = uuid.uuid4()
    with admin_session() as s:
        s.execute(
            text("INSERT INTO tenant (id, name) VALUES (:id, :n)"),
            [{"id": a, "n": "Tenant A"}, {"id": b, "n": "Tenant B"}],
        )
    yield a, b
    with admin_session() as s:
        s.execute(text("DELETE FROM company WHERE tenant_id IN (:a, :b)"), {"a": a, "b": b})
        s.execute(text("DELETE FROM tenant WHERE id IN (:a, :b)"), {"a": a, "b": b})
