"""IntegrityService — consulta e cacheia dados públicos de contraparte (CNPJ).

Fontes (Fase atual): Receita/QSA via BrasilAPI (sem chave). CEIS/CNEP entram
quando houver chave do Portal (sancoes fica []/None até lá).

INVARIANTE DE CONFIABILIDADE: se a fonte falha, o status vira 'indisponivel' e o
dado bom anterior é preservado — NUNCA se infere "ativo/sem sanção" de uma falha.
"""

from __future__ import annotations

import re
from datetime import timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.secrets import get_secret_provider
from app.core.timeutils import now_utc
from app.integrity.sanctions import fetch_sanctions
from app.models.integrity import Counterparty

log = get_logger("integrity")

TTL = timedelta(days=30)
BRASILAPI = "https://brasilapi.com.br/api/cnpj/v1"


def only_digits(doc: str | None) -> str:
    return re.sub(r"\D", "", doc or "")


def is_cnpj(doc: str | None) -> bool:
    return len(only_digits(doc)) == 14


def _mask_doc(doc: str | None) -> str | None:
    d = only_digits(doc)
    if not d:
        return doc  # Receita já costuma mascarar (ex.: ***456789**)
    if len(d) == 11:
        return f"***{d[3:9]}**"  # CPF mascarado (LGPD)
    return doc


def parse_brasilapi(p: dict) -> dict:
    """Puro: payload BrasilAPI -> campos canônicos de contraparte (LGPD: QSA mínimo)."""
    qsa = []
    for s in p.get("qsa") or []:
        qsa.append(
            {
                "nome": s.get("nome_socio"),
                "doc": _mask_doc(s.get("cnpj_cpf_do_socio")),
                "qualificacao": s.get("qualificacao_socio"),
                "entrada": s.get("data_entrada_sociedade"),
            }
        )
    return {
        "razao_social": p.get("razao_social"),
        "situacao_cadastral": p.get("descricao_situacao_cadastral"),
        "data_abertura": p.get("data_inicio_atividade"),
        "cnae": p.get("cnae_fiscal_descricao"),
        "qsa": qsa,
    }


def _fresh(cp: Counterparty) -> bool:
    return cp.status == "ok" and cp.checked_at is not None and (now_utc() - cp.checked_at) < TTL


def check(session: Session, cnpj_raw: str) -> Counterparty | None:
    cnpj = only_digits(cnpj_raw)
    if len(cnpj) != 14:
        return None  # CPF/inválido: integridade PJ não se aplica aqui
    existing = session.execute(
        select(Counterparty).where(Counterparty.cnpj == cnpj)
    ).scalar_one_or_none()
    if existing and _fresh(existing):
        return existing

    try:
        with httpx.Client(timeout=20) as c:
            r = c.get(f"{BRASILAPI}/{cnpj}")
        if r.status_code == 404:
            data, status = {"razao_social": None, "situacao_cadastral": "NAO_ENCONTRADO"}, "ok"
        else:
            r.raise_for_status()
            data, status = parse_brasilapi(r.json()), "ok"
    except httpx.HTTPError as e:
        # FALHA: nunca marcar como limpo. Preserva dado bom anterior; senão, "indisponivel".
        log.warning("integrity.source_unavailable", cnpj=cnpj, error=str(e))
        if existing:
            existing.status = "indisponivel"
            existing.checked_at = now_utc()
            return existing
        cp = Counterparty(
            cnpj=cnpj, status="indisponivel", source="brasilapi", checked_at=now_utc()
        )
        session.add(cp)
        session.flush()
        return cp

    cp = existing or Counterparty(cnpj=cnpj)
    cp.razao_social = data.get("razao_social")
    cp.situacao_cadastral = data.get("situacao_cadastral")
    cp.data_abertura = data.get("data_abertura")
    cp.cnae = data.get("cnae")
    cp.qsa = data.get("qsa")
    # sanções (CEIS/CNEP): None = não verificado; [] = nenhuma; [..] = sancionado.
    # Sem chave, fetch_sanctions devolve None -> NÃO inferimos "limpo".
    api_key = get_secret_provider().get_optional("portal/transparencia/api_key")
    sanc = fetch_sanctions(cnpj, api_key)
    if sanc is not None:
        cp.sancoes = sanc
    cp.status = status
    cp.source = "brasilapi"
    cp.checked_at = now_utc()
    if existing is None:
        session.add(cp)
    session.flush()
    return cp


def refresh_for_tenant(session: Session, tenant_id: str, limit: int | None = None) -> dict:
    """Atualiza counterparty para os fornecedores (CNPJ) do tenant. Read-only nas
    fontes; cacheado. Roda em background (não bloqueia auditoria)."""
    from app.models.sourcing import Creditor

    rows = (
        session.execute(select(Creditor.cnpj_cpf).where(Creditor.cnpj_cpf.is_not(None)).distinct())
        .scalars()
        .all()
    )
    cnpjs = [d for d in rows if is_cnpj(d)]
    if limit:
        cnpjs = cnpjs[:limit]
    ok = unavailable = 0
    for d in cnpjs:
        cp = check(session, d)
        if cp and cp.status == "ok":
            ok += 1
        elif cp:
            unavailable += 1
    log.info("integrity.refresh.done", tenant_id=tenant_id, ok=ok, unavailable=unavailable)
    return {"checked": len(cnpjs), "ok": ok, "unavailable": unavailable}
