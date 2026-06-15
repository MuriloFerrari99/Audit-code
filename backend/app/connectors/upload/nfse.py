"""Parser de NFS-e (nota de serviço). Tolerante a namespace e a variações.

NFS-e NÃO é unificada como a NF-e: existe o padrão ABRASF (a maioria) e dezenas
de variantes municipais. Para não quebrar por namespace/prefixo, lemos por
*local-name* (ignora xmlns) e aceitamos sinônimos de campo. Mapeia para o MESMO
dict canônico do parser de NF-e -> reaproveita toda a carga e as regras.

Fase A: cobre o essencial (prestador, valor do serviço, retenções ISS/INSS/
federais, discriminação). Variantes exóticas caem em dead-letter (visível).
"""

from __future__ import annotations

from typing import Any

from defusedxml.ElementTree import fromstring as safe_fromstring

from app.connectors.upload.nfe import _find, _text  # helpers por local-name


def _first_text(el, names: list[str]) -> str | None:
    for n in names:
        v = _text(el, n)
        if v is not None:
            return v
    return None


def looks_like_nfse(content: bytes | str) -> bool:
    head = content[:4000].decode("utf-8", "ignore") if isinstance(content, bytes) else content[:4000]
    return ("InfNfse" in head or "Nfse" in head or "infNfse" in head) and "infNFe" not in head


def parse_nfse(xml: str | bytes) -> dict[str, Any]:
    """XML NFS-e (ABRASF/variantes) -> dict canônico (mesmas chaves do parse_nfe)."""
    root = safe_fromstring(xml)
    inf = _find(root, "InfNfse") or _find(root, "infNfse") or _find(root, "Nfse")
    if inf is None:
        raise ValueError("XML sem InfNfse — não parece NFS-e")

    numero = _first_text(inf, ["Numero", "NumeroNfse"])
    cod = _text(inf, "CodigoVerificacao")
    chave = "-".join(p for p in (numero, cod) if p) or None

    prest = _find(inf, "PrestadorServico") or _find(inf, "Prestador")
    emit_cnpj = _first_text(prest or inf, ["Cnpj", "Cpf", "CpfCnpj"])
    emit_nome = _first_text(prest or inf, ["RazaoSocial", "NomeFantasia", "Nome"])

    servico = _find(inf, "Servico") or inf
    valores = _find(servico, "Valores") or servico

    valor = _first_text(valores, ["ValorServicos", "ValorLiquidoNfse"]) or _text(inf, "ValorLiquidoNfse")
    iss_retido = _first_text(valores, ["IssRetido", "ResponsavelRetencao"])  # 1=sim, 2=não
    valor_iss = _first_text(valores, ["ValorIss", "ValorIssRetido"])
    # ISS só conta como "retido" quando o tomador reteve (IssRetido=1) ou veio em campo de retenção
    iss = valor_iss if (iss_retido == "1" or _text(valores, "ValorIssRetido")) else None

    discriminacao = _first_text(servico, ["Discriminacao", "Descricao"]) or "(serviço)"
    cod_servico = _first_text(servico, ["ItemListaServico", "CodigoTributacaoMunicipio"])

    return {
        "chave": chave,
        "numero": numero,
        "serie": None,
        "emissao": _first_text(inf, ["DataEmissao", "Competencia"]),
        "natureza": "Servico (NFS-e)",  # ASCII p/ casar is_service na carga (sem cedilha)
        "emit_cnpj": emit_cnpj,
        "emit_nome": emit_nome,
        "dest_cnpj": None,
        "dest_nome": None,
        "valor_produtos": None,
        "valor_icms": None,
        "valor_ipi": None,
        "valor_total": valor,
        "retencoes": {
            "inss": _first_text(valores, ["ValorInss"]),  # quando presente, é retido
            "pis": _first_text(valores, ["ValorPis"]),
            "cofins": _first_text(valores, ["ValorCofins"]),
            "csll": _first_text(valores, ["ValorCsll"]),
            "irrf": _first_text(valores, ["ValorIr", "ValorIrrf"]),
            "iss": iss,
        },
        "itens": [
            {
                "item": "1",
                "codigo": cod_servico,
                "descricao": discriminacao[:500],
                "ncm": None,
                "cfop": None,
                "unidade": None,
                "qtd": "1",
                "valor_unit": valor,
                "valor_total": valor,
            }
        ],
    }
