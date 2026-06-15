"""Smoke test do app FastAPI: precisa IMPORTAR e expor as rotas esperadas.

Guarda contra bug latente de import (ex.: Role importado do módulo errado) que
não aparece nos testes de unidade porque eles não sobem o app HTTP.
"""

from __future__ import annotations


def test_app_imports_and_exposes_routes():
    import app.main as m

    paths = set(m.app.openapi()["paths"].keys())
    for expected in (
        "/healthz",
        "/auth/login",
        "/findings",
        "/upload/nfe",
        "/upload/planilha",
        "/billing/me",
        "/billing/statement",
        "/billing/checkout",
        "/billing/webhook/stripe",
        "/admin/tenants",
        "/admin/plans",
        "/disputes",
    ):
        assert expected in paths, f"rota ausente: {expected}"
