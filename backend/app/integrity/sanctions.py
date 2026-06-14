"""Sanções de fornecedor: CEIS/CNEP (Portal da Transparência).

Exige a chave gratuita do Portal (header `chave-api-dados`), via SecretProvider
(path 'portal/transparencia/api_key' / env PORTAL_TRANSPARENCIA_KEY).

CONFIABILIDADE (encoding honesto de "verificado vs não"):
- retorno None  -> sanção NÃO verificada (sem chave ou fonte indisponível)
- retorno []    -> verificado: nenhuma sanção
- retorno [..]  -> sancionado (lista de sanções)
Nunca tratar None como "limpo".

O parser é tolerante a variações de campo; a forma exata é confirmada na 1ª
resposta real (ver scripts/ceis_check.py).
"""

from __future__ import annotations

import httpx

from app.core.logging import get_logger

log = get_logger("integrity.sanctions")

BASE = "https://api.portaldatransparencia.gov.br/api-de-dados"
SOURCES = {"CEIS": "/ceis", "CNEP": "/cnep"}


def _first(d: dict, *keys):
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return None


def _norm_record(fonte: str, r: dict) -> dict:
    pessoa = r.get("pessoa") or {}
    sancao = r.get("sancao") or r
    orgao = r.get("orgaoSancionador") or sancao.get("orgaoSancionador") or {}
    tipo = r.get("tipoSancao") or sancao.get("tipoSancao") or {}
    return {
        "fonte": fonte,
        "tipo": tipo.get("descricaoResumida") if isinstance(tipo, dict) else (tipo or None),
        "orgao": orgao.get("nome") if isinstance(orgao, dict) else (orgao or None),
        "data_inicio": _first(sancao, "dataInicioSancao", "dataPublicacaoSancao"),
        "data_fim": _first(sancao, "dataFimSancao"),
        "fundamentacao": _first(r, "fundamentacao", "textoPublicacao"),
        "nome": _first(pessoa, "nome", "razaoSocialReceita"),
    }


def fetch_sanctions(cnpj: str, api_key: str | None) -> list[dict] | None:
    """Consulta CEIS+CNEP por CNPJ. None = não verificado (sem chave/fonte fora)."""
    if not api_key:
        return None
    found: list[dict] = []
    try:
        with httpx.Client(timeout=25, headers={"chave-api-dados": api_key}) as c:
            for fonte, path in SOURCES.items():
                r = c.get(f"{BASE}{path}", params={"cnpjSancionado": cnpj, "pagina": 1})
                if r.status_code == 401:
                    log.warning("sanctions.unauthorized", note="chave inválida")
                    return None
                r.raise_for_status()
                data = r.json()
                rows = data if isinstance(data, list) else data.get("registros", [])
                for rec in rows:
                    found.append(_norm_record(fonte, rec))
    except httpx.HTTPError as e:
        log.warning("sanctions.source_unavailable", cnpj=cnpj, error=str(e))
        return None  # NÃO verificado — nunca inferir "limpo"
    return found
