"""Base legal por regra (explicabilidade exigida por grandes contas).

Mapeia rule_id -> fundamentos legais citáveis. Anexado ao achado (legal_citations)
e usável pelo Agente Executor na peça de contestação. Conteúdo é por país/setor;
hoje BR/construção. Mantido conservador — só citamos o que sustenta a regra.
"""

from __future__ import annotations

LEGAL_CITATIONS: dict[str, list[str]] = {
    # Retenções (dimensão fiscal)
    "RET1": [
        "IN RFB nº 971/2009, art. 112 e seg. (retenção de 11% de INSS na cessão de mão de obra)",
        "Lei nº 8.212/1991, art. 31 (retenção previdenciária)",
    ],
    "RET2": [
        "LC nº 116/2003, art. 3º e art. 6º (ISS — local da prestação e responsabilidade por retenção)",
    ],
    # Fiscal / documento
    "F1": ["Divergência nota×pedido — base contratual do pedido de compra"],
    "F2": ["Inconsistência declarada pelo emissor (validação SEFAZ)"],
    "F3": ["Divergência nota×pagamento — pagamento acima do documento fiscal"],
}


def citations_for(rule_id: str) -> list[str] | None:
    cites = LEGAL_CITATIONS.get(rule_id)
    return list(cites) if cites else None
