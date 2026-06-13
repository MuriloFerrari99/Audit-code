"""Normalização determinística de descrição de insumo (T-081, ml.md Job 1).

Primeira etapa da cascata de casamento: limpa e padroniza (uppercase, unidades,
bitolas, sinônimos óbvios). Pega os casos fáceis antes de gastar embedding/LLM.
"""

from __future__ import annotations

import re

_SYNONYMS = {
    "vergalhao": "aco ca-50",
    "verg": "aco ca-50",
    "cimento portland": "cimento",
    "cp-ii": "cimento cp-ii",
}

_UNIT_PATTERNS = [
    (re.compile(r"\b(\d+(?:[.,]\d+)?)\s*mm\b"), r"\1mm"),
    (re.compile(r"\b(\d+(?:[.,]\d+)?)\s*kg\b"), r"\1kg"),
    (re.compile(r"\bø\s*(\d+)"), r"\1mm"),
]


def normalize_description(raw: str) -> str:
    s = raw.strip().lower()
    s = s.replace("ø", "ø")  # mantém símbolo p/ regra de bitola abaixo
    for pat, repl in _UNIT_PATTERNS:
        s = pat.sub(repl, s)
    for k, v in _SYNONYMS.items():
        s = s.replace(k, v)
    s = re.sub(r"[^a-z0-9\s\-.,]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s
