"""Mapeadores formato-bruto -> CDM. Cada mapper é parte de um Adapter de entrada.

Hoje cobre NF-e/NFS-e (dict do parser) e planilha (linha). Novos formatos
(PDF US, EDI) entram aqui sem tocar o Core nem o banco.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.canonical.document import (
    CanonicalDocument,
    CanonicalItem,
    CanonicalParty,
    CanonicalRetentions,
    DocumentType,
    SourceFormat,
)


def _dec(v: Any) -> Decimal | None:
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def fiscal_dict_to_canonical(d: dict, source_format: SourceFormat) -> CanonicalDocument:
    """dict do parse_nfe/parse_nfse -> CanonicalDocument."""
    ret = d.get("retencoes") or {}
    is_service = source_format == SourceFormat.NFSE or "servic" in (d.get("natureza") or "").lower()
    items = [
        CanonicalItem(
            description=it.get("descricao") or "(item)",
            code=it.get("codigo"),
            classification=it.get("ncm") or it.get("cfop"),
            quantity=_dec(it.get("qtd")),
            unit=it.get("unidade"),
            unit_price=_dec(it.get("valor_unit")),
            total=_dec(it.get("valor_total")),
        )
        for it in (d.get("itens") or [])
    ]
    return CanonicalDocument(
        source_format=source_format,
        document_type=DocumentType.SERVICE_INVOICE if is_service else DocumentType.GOODS_INVOICE,
        external_id=d.get("chave") or "",
        country="BR",
        currency="BRL",
        number=d.get("numero"),
        series=d.get("serie"),
        issuer=CanonicalParty(name=d.get("emit_nome"), tax_id=d.get("emit_cnpj"), country="BR"),
        recipient=CanonicalParty(name=d.get("dest_nome"), tax_id=d.get("dest_cnpj"), country="BR"),
        total_amount=_dec(d.get("valor_total")),
        items=items,
        retentions=CanonicalRetentions(
            inss=_dec(ret.get("inss")), iss=_dec(ret.get("iss")),
            pis=_dec(ret.get("pis")), cofins=_dec(ret.get("cofins")),
            csll=_dec(ret.get("csll")), irrf=_dec(ret.get("irrf")),
        ),
        is_service=is_service,
        raw_ref=d.get("chave"),
    )
