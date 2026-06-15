"""Testa o parser BrasilAPI -> contraparte contra a estrutura REAL (validada na
API). Puro (sem rede/DB). Confirma minimização LGPD do QSA (CPF mascarado)."""

from __future__ import annotations

from app.integrity.service import _mask_doc, is_cnpj, only_digits, parse_brasilapi

REAL = {
    "razao_social": "SOFTPLAN PLANEJAMENTO E SISTEMAS S/A",
    "descricao_situacao_cadastral": "ATIVA",
    "data_inicio_atividade": "1990-11-28",
    "cnae_fiscal_descricao": "Desenvolvimento de programas de computador sob encomenda",
    "qsa": [
        {
            "nome_socio": "ANDREY N DE ABREU",
            "cnpj_cpf_do_socio": "***627369**",
            "qualificacao_socio": "Diretor",
            "data_entrada_sociedade": "2020-02-02",
        }
    ],
}


def test_parse_and_mask():
    out = parse_brasilapi(REAL)
    assert out["situacao_cadastral"] == "ATIVA"
    assert out["data_abertura"] == "1990-11-28"
    socio = out["qsa"][0]
    assert socio["nome"] == "ANDREY N DE ABREU"
    assert "627369" in socio["doc"]  # mantém masked, nunca CPF cheio
    assert _mask_doc("12345678901") == "***456789**"
    assert only_digits("82.845.322/0001-04") == "82845322000104"
    assert is_cnpj("82.845.322/0001-04") is True
    assert is_cnpj("123.456.789-01") is False
