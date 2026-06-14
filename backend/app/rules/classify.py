"""Classificação leve de insumo (redução de falso-positivo — auditoria A-1).

Insumos de serviço/mão de obra/empreitada não passam por cotação de material e
têm preço unitário heterogêneo; não devem alimentar R1 (sobrepreço) nem R6
(sem concorrência). Heurística por descrição, acento-insensível. Configurável
no futuro por tenant/categoria do ERP.
"""

from __future__ import annotations

import unicodedata

NON_MATERIAL = (
    "mao de obra", "m.o", "servico", "empreitada", "locacao", "aluguel",
    "alimentacao", "frete", "taxa", "imposto", "medicao", "terceiriz",
    "consultoria", "honorario", "comissao", "mensalidade", "manutencao",
    "transporte", "diaria", "hospedagem",
)

# Se max/min do preço do mesmo insumo passar disto, o código de insumo mistura
# itens diferentes -> mediana inválida -> não usar p/ sobrepreço.
DISPERSION_MAX = 12.0
# Ratio acima disto entre preço pago e cotação = produto/unidade diferente.
RATIO_MAX = 30.0


def _norm(s: str | None) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", (s or "").lower())
        if not unicodedata.combining(c)
    )


def is_non_material(description: str | None) -> bool:
    n = _norm(description)
    return any(k in n for k in NON_MATERIAL)
