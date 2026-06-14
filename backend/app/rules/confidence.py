"""Score de confiança por achado (Módulo B — docs/evolucao-modulos.md).

Confiança explicável a partir de features do próprio achado. Achados de baixa
confiança vão para "a investigar" (não para a cara do cliente). É o que evita
"dado burro" HOJE, sem depender de Deep Learning. Quando houver rótulos
(finding_review) por tenant, este score vira alvo de um ranker aprendido.
"""

from __future__ import annotations

# confiança-base por regra (quão "dura" é a evidência da regra)
_BASE = {
    "R1": 0.60,  # sobrepreço vs mediana
    "R2": 0.70,  # cotação perdida (evidência concreta)
    "R3": 0.50,  # fracionamento (heurístico)
    "R4": 0.70,  # estouro medido vs orçado
    "R5": 0.80,  # divergência pedido->pagamento (cadeia direta)
    "R6": 0.45,  # sem concorrência (governança, não perda)
}

THRESHOLD = 0.55  # abaixo disto -> "a investigar"


def score(rule_id: str, reference_snapshot: dict | None) -> float:
    c = _BASE.get(rule_id, 0.5)
    ref = reference_snapshot or {}
    layer = ref.get("layer", "")
    # referência pública/curada é mais confiável que mediana interna
    if "sinapi" in str(ref.get("source", "")).lower() or layer == "camada_1_sinapi":
        c += 0.20
    # mediana interna: mais amostra = mais confiança
    n = ref.get("n")
    if isinstance(n, int):
        if n >= 10:
            c += 0.15
        elif n >= 5:
            c += 0.05
        else:
            c -= 0.10
    return max(0.0, min(1.0, round(c, 3)))


def label(confidence: float) -> str:
    if confidence >= 0.75:
        return "alta"
    if confidence >= THRESHOLD:
        return "media"
    return "baixa"
