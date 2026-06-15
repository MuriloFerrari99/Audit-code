"""Fase 1 — parser/carga de planilha ERP (CSV/XLSX) -> canônico (Bill).

Cobre: auto-detecção de colunas, valores em formato BR, carga ao canônico,
dead-letter de linha inválida, idempotência de reupload e o caminho XLSX.
"""

from __future__ import annotations

import contextlib
import io
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.connectors.upload.load import load_spreadsheet
from app.connectors.upload.spreadsheet import (
    detect_mapping,
    parse_amount,
    parse_spreadsheet,
)
from app.core.db import tenant_session
from app.findings.service import list_findings
from app.rules.engine import run_all
from app.rules.payment_rules import register_payment_rules
from scripts.seed_synthetic import TENANT_ID, seed

CSV = (
    "Fornecedor;CNPJ;Nota Fiscal;Valor;Vencimento;Pedido\n"
    "Concreteira ABC;14200166000187;NF-555;1.250,50;10/05/2026;\n"
    "Concreteira ABC;14200166000187;NF-555;1.250,50;10/05/2026;\n"  # duplicada -> P1
    "Aço Forte LTDA;09999999000191;NF-777;R$ 8.000,00;20/05/2026;\n"
    "Linha Ruim;;;;;\n"  # sem valor -> dead-letter
)


@pytest.fixture(scope="module", autouse=True)
def _register():
    with contextlib.suppress(ValueError):
        register_payment_rules()


@pytest.fixture
def seeded():
    return seed()


# ---------------------------------------------------------------- parser puro
def test_parse_amount_br():
    assert parse_amount("1.250,50") == Decimal("1250.50")
    assert parse_amount("R$ 8.000,00") == Decimal("8000.00")
    assert parse_amount("1234.56") == Decimal("1234.56")
    assert parse_amount(1500) == Decimal("1500")
    assert parse_amount("") is None
    assert parse_amount("abc") is None


def test_detect_mapping_synonyms():
    m = detect_mapping(["Fornecedor", "CNPJ", "Nota Fiscal", "Valor", "Vencimento", "Pedido"])
    assert m["fornecedor"] == "Fornecedor"
    assert m["cnpj"] == "CNPJ"
    assert m["documento"] == "Nota Fiscal"
    assert m["valor"] == "Valor"
    assert m["data"] == "Vencimento"


def test_parse_spreadsheet_csv():
    p = parse_spreadsheet("lancamentos.csv", CSV.encode())
    assert p["mapping"]["valor"] == "Valor"
    assert len(p["rows"]) == 4
    assert p["rows"][0]["fornecedor"] == "Concreteira ABC"


# ---------------------------------------------------------------- carga + DB
def test_load_creates_bills_and_dead_letter(seeded):
    summary = load_spreadsheet(str(TENANT_ID), "lancamentos.csv", CSV.encode())
    assert summary["bills"] == 3  # 3 linhas válidas
    assert summary["dead_letters"] == 1  # linha sem valor
    with tenant_session(str(TENANT_ID)) as s:
        n = s.execute(
            text("SELECT count(*) FROM bill WHERE source = 'upload'")
        ).scalar_one()
        assert n == 3


def test_reupload_is_idempotent(seeded):
    load_spreadsheet(str(TENANT_ID), "lancamentos.csv", CSV.encode())
    load_spreadsheet(str(TENANT_ID), "lancamentos.csv", CSV.encode())
    with tenant_session(str(TENANT_ID)) as s:
        n = s.execute(
            text("SELECT count(*) FROM bill WHERE source = 'upload'")
        ).scalar_one()
    assert n == 3, "reupload duplicou títulos"


def test_duplicate_line_triggers_p1(seeded):
    load_spreadsheet(str(TENANT_ID), "lancamentos.csv", CSV.encode())
    with tenant_session(str(TENANT_ID)) as s:
        run_all(s, str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        rules = {f.rule_id for f in list_findings(s, limit=1000)}
    assert "P1" in rules, "duas linhas idênticas deveriam disparar P1 (duplicado)"


def test_xlsx_path(seeded):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Fornecedor", "CNPJ", "Documento", "Valor", "Data"])
    ws.append(["Fornecedor XLSX", "11222333000181", "NF-900", 4321.0, "15/05/2026"])
    buf = io.BytesIO()
    wb.save(buf)
    summary = load_spreadsheet(str(TENANT_ID), "lanc.xlsx", buf.getvalue())
    assert summary["bills"] == 1
    assert summary["mapping"]["documento"] == "Documento"
