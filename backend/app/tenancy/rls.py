"""Helpers de Row-Level Security (ADR-08, T-031).

Gera o SQL que habilita RLS por tenant em uma tabela. Usa
`current_setting('app.current_tenant', true)` (o segundo arg = missing_ok),
de modo que, sem tenant fixado, a comparação vira NULL e NENHUMA linha é
visível — fail-closed.

FORCE ROW LEVEL SECURITY é essencial: em dev a role da app é dona da tabela,
e sem FORCE o dono ignora o RLS.
"""

from __future__ import annotations

POLICY_SUFFIX = "_tenant_isolation"


def enable_rls_statements(table: str) -> list[str]:
    policy = f"{table}{POLICY_SUFFIX}"
    expr = "tenant_id = current_setting('app.current_tenant', true)::uuid"
    return [
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;",
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;",
        f"DROP POLICY IF EXISTS {policy} ON {table};",
        # SELECT/UPDATE/DELETE: só linhas do tenant atual.
        # INSERT: WITH CHECK garante que não se insere para outro tenant.
        f"CREATE POLICY {policy} ON {table} USING ({expr}) WITH CHECK ({expr});",
    ]


def disable_rls_statements(table: str) -> list[str]:
    policy = f"{table}{POLICY_SUFFIX}"
    return [
        f"DROP POLICY IF EXISTS {policy} ON {table};",
        f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;",
        f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;",
    ]
