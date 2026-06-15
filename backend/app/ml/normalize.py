"""Normalização determinística de descrição de insumo (T-081, ml.md Job 1).

Primeira etapa da cascata de casamento: remove acento, padroniza unidades/
bitolas e aplica sinônimos por limite de palavra. Pega os casos fáceis antes de
gastar embedding/LLM.
"""

from __future__ import annotations

import re
import unicodedata

# Sinônimos aplicados por palavra inteira (evita substituir dentro de outra palavra).
_SYNONYMS = {
    "vergalhao": "aco ca-50",
    "verg": "aco ca-50",
}

_BITOLA = re.compile(r"ø\s*(\d+(?:[.,]\d+)?)")
_UNIT = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*(mm|kg|cm|m|m2|m3|sc|un|l)\b")


def _strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_description(raw: str) -> str:
    s = _strip_accents(raw).lower()
    s = _BITOLA.sub(r"\1mm", s)  # Ø10 -> 10mm
    s = _UNIT.sub(r"\1\2", s)  # "10.0 mm" -> "10.0mm"
    # sinônimos por palavra inteira
    for src, dst in _SYNONYMS.items():
        s = re.sub(rf"\b{src}\b", dst, s)
    s = re.sub(r"[^a-z0-9\s\-.,]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s
