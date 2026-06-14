"""Sync real do Sienge (Alumbra) -> canônico -> regras -> achados.

Roda no container. Carrega uma fatia (default 300 pedidos) para a 1ª execução
ser rápida; aumente o limite quando validar.

Uso: python -m scripts.sync_alumbra [max_orders]
"""

from __future__ import annotations

import sys

from app.connectors.sienge.connector import SiengeConnector
from app.connectors.sienge.load import load_canonical
from app.core.db import tenant_session
from app.core.secrets import get_secret_provider
from app.rules.builtin import register_builtin_rules
from app.rules.engine import run_all

TENANT = "11111111-1111-1111-1111-111111111111"


def main() -> None:
    max_orders = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    secrets = get_secret_provider()
    connector = SiengeConnector(TENANT, secrets, use_fixtures=False)

    print(f"[1/3] carregando canônico do Sienge (até {max_orders} pedidos)...")
    summary = load_canonical(connector, TENANT, max_orders=max_orders)
    print("      carga:", summary)

    try:
        register_builtin_rules()
    except ValueError:
        pass

    print("[2/3] rodando as 6 regras sobre o dado real...")
    with tenant_session(TENANT) as s:
        found = run_all(s, TENANT)
    print("      achados por regra:", found)
    print("[3/3] pronto. Veja em http://localhost:3000 (ou /findings na API).")


if __name__ == "__main__":
    main()
