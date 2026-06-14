"""Teste de isolamento multi-tenant (T-033) — gate de aceite (prd.md §9).

Prova que, com RLS ativo:
  1. cada tenant só LÊ as próprias linhas;
  2. um tenant NÃO consegue INSERIR linha marcada para outro tenant (WITH CHECK);
  3. sem tenant fixado, NENHUMA linha de dado de cliente é visível (fail-closed).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from app.core.db import SessionLocal, tenant_session


def _insert_company(session, tenant_id, name):
    session.execute(
        text("INSERT INTO company (id, tenant_id, name, cnpj) VALUES (:id, :t, :n, :c)"),
        {"id": uuid.uuid4(), "t": tenant_id, "n": name, "c": "00.000.000/0001-00"},
    )


def test_runtime_role_is_not_privileged():
    """C-1: o role do runtime NÃO pode ser superusuário nem ter BYPASSRLS —
    senão o Postgres ignora o RLS e o isolamento multi-tenant é fictício.
    SessionLocal usa o engine de aplicação (app_rw)."""
    with SessionLocal() as s:
        row = s.execute(
            text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        ).one()
    assert row.rolsuper is False, "runtime conectado como SUPERUSUÁRIO — RLS é ignorado!"
    assert row.rolbypassrls is False, "runtime com BYPASSRLS — RLS é ignorado!"


def test_tenant_reads_only_its_own_rows(two_tenants):
    a, b = two_tenants
    with tenant_session(str(a)) as s:
        _insert_company(s, a, "Empresa A")
    with tenant_session(str(b)) as s:
        _insert_company(s, b, "Empresa B")

    with tenant_session(str(a)) as s:
        names = {r[0] for r in s.execute(text("SELECT name FROM company"))}
    assert names == {"Empresa A"}

    with tenant_session(str(b)) as s:
        names = {r[0] for r in s.execute(text("SELECT name FROM company"))}
    assert names == {"Empresa B"}


def test_cannot_insert_for_another_tenant(two_tenants):
    a, b = two_tenants
    # Em sessão do tenant A, tentar inserir linha do tenant B deve violar o WITH CHECK.
    with pytest.raises((DBAPIError, ProgrammingError)):
        with tenant_session(str(a)) as s:
            _insert_company(s, b, "Empresa intrusa")


def test_no_tenant_context_sees_nothing(two_tenants):
    a, _ = two_tenants
    with tenant_session(str(a)) as s:
        _insert_company(s, a, "Empresa A")

    # Sessão sem app.current_tenant: fail-closed (NULL -> nenhuma linha).
    session = SessionLocal()
    try:
        count = session.execute(text("SELECT count(*) FROM company")).scalar_one()
        assert count == 0
    finally:
        session.close()
