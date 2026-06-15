"""Probe CEIS/CNEP (Portal da Transparência) — confirma a chave e o FORMATO real
da resposta, para fixar o parser (mesma disciplina do sienge_check).

Pré-requisito: PORTAL_TRANSPARENCIA_KEY no .env (chave gratuita).
Uso: python -m scripts.ceis_check [cnpj]
"""

from __future__ import annotations

import json
import sys

import httpx

from app.core.secrets import get_secret_provider

BASE = "https://api.portaldatransparencia.gov.br/api-de-dados"


def main() -> None:
    cnpj = sys.argv[1] if len(sys.argv) > 1 else "82845322000104"
    key = get_secret_provider().get_optional("portal/transparencia/api_key")
    if not key:
        print(
            "SEM CHAVE. Cadastre em portaldatransparencia.gov.br/api-de-dados/cadastrar-email "
            "e preencha PORTAL_TRANSPARENCIA_KEY no .env."
        )
        return
    with httpx.Client(timeout=25, headers={"chave-api-dados": key}) as c:
        for fonte, path in (("CEIS", "/ceis"), ("CNEP", "/cnep")):
            r = c.get(f"{BASE}{path}", params={"cnpjSancionado": cnpj, "pagina": 1})
            print(f"\n[{fonte}] HTTP {r.status_code}")
            if r.is_success:
                data = r.json()
                rows = data if isinstance(data, list) else data.get("registros", [])
                print(f"  registros: {len(rows)}")
                if rows:
                    print("  campos do 1º registro:", sorted(rows[0].keys()))
                    print("  amostra:", json.dumps(rows[0], ensure_ascii=False)[:400])
            else:
                print("  corpo:", r.text[:200])


if __name__ == "__main__":
    main()
