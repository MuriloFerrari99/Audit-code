"""Sync real do Sienge (Alumbra) -> canônico -> regras -> achados.

Roda no container. Carrega uma fatia (default 300 pedidos) para a 1ª execução
ser rápida; aumente o limite quando validar.

Uso: python -m scripts.sync_alumbra [max_orders]
"""

from __future__ import annotations

import contextlib
import sys

from app.connectors.sienge.connector import SiengeConnector
from app.connectors.sienge.load import load_canonical
from app.core.db import tenant_session
from app.core.secrets import get_secret_provider
from app.integrity.service import refresh_for_tenant
from app.rules.builtin import register_builtin_rules
from app.rules.engine import run_all
from app.rules.fiscal_rules import register_fiscal_rules
from app.rules.integrity_rules import register_integrity_rules
from app.rules.payment_rules import register_payment_rules

TENANT = "11111111-1111-1111-1111-111111111111"


def main() -> None:
    max_orders = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    secrets = get_secret_provider()
    connector = SiengeConnector(TENANT, secrets, use_fixtures=False)

    print(f"[1/3] carregando canônico do Sienge (até {max_orders} pedidos)...")
    summary = load_canonical(connector, TENANT, max_orders=max_orders)
    print("      carga:", summary)

    for reg in (
        register_builtin_rules,
        register_integrity_rules,
        register_fiscal_rules,
        register_payment_rules,
    ):
        with contextlib.suppress(ValueError):
            reg()

    print("[2/4] checando integridade dos fornecedores (Receita/BrasilAPI)...")
    with tenant_session(TENANT) as s:
        integ = refresh_for_tenant(s, TENANT, limit=50)
    print("      integridade:", integ)

    print("[3/4] rodando as regras sobre o dado real...")
    with tenant_session(TENANT) as s:
        found = run_all(s, TENANT)
    print("      achados por regra:", found)
    print("[4/4] pronto. Veja em http://localhost:3000 (ou /findings na API).")


if __name__ == "__main__":
    main()
