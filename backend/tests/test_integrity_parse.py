"""Testa o parser BrasilAPI -> contraparte contra a estrutura REAL (validada na
API). Puro (sem rede/DB). Confirma minimização LGPD do QSA (CPF mascarado)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

# carrega só as funções puras de service.py sem puxar httpx/sqlalchemy
_SRC = Path(__file__).resolve().parent.parent / "app" / "integrity" / "service.py"


def _load_pure():
    import re
    src = _SRC.read_text()
    src = (src
           .replace("import httpx", "")
           .replace("from sqlalchemy import select", "")
           .replace("from sqlalchemy.orm import Session", "")
           .replace("from app.core.logging import get_logger",
                    "def get_logger(*a, **k):\n import types;return types.SimpleNamespace(warning=lambda *a, **k: None, info=lambda *a, **k: None)")
           .replace("from app.core.timeutils import now_utc",
                    "from datetime import datetime, timezone\ndef now_utc():return datetime.now(timezone.utc)")
           .replace("from app.models.integrity import Counterparty", "class Counterparty:pass"))
    ns = {"re": re}
    exec(compile(src, "<svc>", "exec"), ns)  # noqa: S102
    return ns


REAL = {
    "razao_social": "SOFTPLAN PLANEJAMENTO E SISTEMAS S/A",
    "descricao_situacao_cadastral": "ATIVA",
    "data_inicio_atividade": "1990-11-28",
    "cnae_fiscal_descricao": "Desenvolvimento de programas de computador sob encomenda",
    "qsa": [{"nome_socio": "ANDREY N DE ABREU", "cnpj_cpf_do_socio": "***627369**",
             "qualificacao_socio": "Diretor", "data_entrada_sociedade": "2020-02-02"}],
}


def test_parse_and_mask():
    ns = _load_pure()
    out = ns["parse_brasilapi"](REAL)
    assert out["situacao_cadastral"] == "ATIVA"
    assert out["data_abertura"] == "1990-11-28"
    socio = out["qsa"][0]
    assert socio["nome"] == "ANDREY N DE ABREU"
    assert "627369" in socio["doc"]  # mantém masked, nunca CPF cheio
    assert ns["_mask_doc"]("12345678901") == "***456789**"
    assert ns["only_digits"]("82.845.322/0001-04") == "82845322000104"
    assert ns["is_cnpj"]("82.845.322/0001-04") is True
    assert ns["is_cnpj"]("123.456.789-01") is False
