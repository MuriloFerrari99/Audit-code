"""Probe de conexão com o Sienge (read-only).

Autentica com as credenciais do .env e puxa uma amostra de cada entidade,
imprimindo a SAÚDE e o FORMATO da resposta (chaves de campo). É o que falta
para fixar o mapeamento campo a campo (normalize) contra a API real.

Pré-requisito no .env:
    SIENGE_DEFAULT_SUBDOMAIN=...
    SIENGE_DEFAULT_USER=...
    SIENGE_DEFAULT_PASSWORD=...

Uso: python -m scripts.sienge_check [tenant_id]
"""

from __future__ import annotations

import sys

from app.connectors.base import PullCursor
from app.connectors.sienge import SiengeConnector
from app.core.secrets import get_secret_provider

DEFAULT_TENANT = "11111111-1111-1111-1111-111111111111"


def main() -> None:
    tenant_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TENANT
    secrets = get_secret_provider()
    has_creds = secrets.get_optional(f"tenant/{tenant_id}/sienge/subdomain") is not None
    if not has_creds:
        print("SEM CREDENCIAIS. Preencha SIENGE_DEFAULT_SUBDOMAIN/USER/PASSWORD no .env.")
        print("(O conector cairia em modo fixtures, que não toca a API real.)")
        return

    connector = SiengeConnector(tenant_id, secrets, use_fixtures=False)
    health = connector.health()
    print(f"HEALTH: ok={health.ok} detail={health.detail}")
    if not health.ok:
        return

    for entity in connector.list_entities():
        try:
            sample = []
            for i, raw in enumerate(connector.pull(entity, PullCursor())):
                sample.append(raw)
                if i >= 1:  # 2 registros bastam para ver o formato
                    break
            if sample:
                keys = sorted(sample[0].payload.keys())
                print(f"\n[{entity.value}] {len(sample)} amostra(s); campos: {keys}")
            else:
                print(f"\n[{entity.value}] vazio")
        except Exception as e:
            print(f"\n[{entity.value}] ERRO: {e}")


if __name__ == "__main__":
    main()
