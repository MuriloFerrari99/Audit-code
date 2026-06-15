"""Parser de NF-e (XML 4.00 nacional). Puro (stdlib) e testável.

NF-e é padronizada (namespace http://www.portalfiscal.inf.br/nfe), então UM parser
serve para todas. Extrai cabeçalho, itens, totais e RETENÇÕES (INSS/ISS) — base p/
auditoria fiscal e de preço sobre a nota.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET  # apenas para tipos (Element)
from typing import Any

from defusedxml.ElementTree import fromstring as safe_fromstring  # XXE-safe p/ XML não-confiável


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]  # remove namespace


def _find(el: ET.Element, name: str) -> ET.Element | None:
    for child in el.iter():
        if _local(child.tag) == name:
            return child
    return None


def _text(el: ET.Element | None, name: str) -> str | None:
    if el is None:
        return None
    node = _find(el, name)
    return node.text.strip() if node is not None and node.text else None


def parse_nfe(xml: str | bytes) -> dict[str, Any]:
    """XML NF-e -> dict canônico (cabeçalho + itens + totais + retenções)."""
    root = safe_fromstring(xml)
    inf = _find(root, "infNFe")
    if inf is None:
        raise ValueError("XML sem infNFe — não parece NF-e")

    chave = (inf.get("Id") or "").replace("NFe", "") or None
    ide = _find(inf, "ide")
    emit = _find(inf, "emit")
    dest = _find(inf, "dest")
    total = _find(inf, "total")
    ret = _find(total, "retTrib") if total is not None else None

    itens = []
    for det in inf.iter():
        if _local(det.tag) != "det":
            continue
        prod = _find(det, "prod")
        if prod is None:
            continue
        itens.append({
            "item": det.get("nItem"),
            "codigo": _text(prod, "cProd"),
            "descricao": _text(prod, "xProd"),
            "ncm": _text(prod, "NCM"),
            "cfop": _text(prod, "CFOP"),
            "unidade": _text(prod, "uCom"),
            "qtd": _text(prod, "qCom"),
            "valor_unit": _text(prod, "vUnCom"),
            "valor_total": _text(prod, "vProd"),
        })

    return {
        "chave": chave,
        "numero": _text(ide, "nNF"),
        "serie": _text(ide, "serie"),
        "emissao": _text(ide, "dhEmi") or _text(ide, "dEmi"),
        "natureza": _text(ide, "natOp"),
        "emit_cnpj": _text(emit, "CNPJ") or _text(emit, "CPF"),
        "emit_nome": _text(emit, "xNome"),
        "dest_cnpj": _text(dest, "CNPJ") or _text(dest, "CPF"),
        "dest_nome": _text(dest, "xNome"),
        "valor_produtos": _text(total, "vProd"),
        "valor_icms": _text(total, "vICMS"),
        "valor_ipi": _text(total, "vIPI"),
        "valor_total": _text(total, "vNF"),
        "retencoes": {
            "inss": _text(ret, "vRetPrev"),   # retenção previdenciária (INSS)
            "pis": _text(ret, "vRetPIS"),
            "cofins": _text(ret, "vRetCOFINS"),
            "csll": _text(ret, "vRetCSLL"),
            "irrf": _text(ret, "vIRRF"),
            "iss": _text(total, "vISSRet") if total is not None else None,
        },
        "itens": itens,
    }
