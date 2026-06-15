"""Fase 1 — upload de NF-e -> canônico -> regras de retenção (RET1/RET2).

Prova o fluxo novo: sobe um XML de NF-e de SERVIÇO sem retenção de INSS/ISS,
audita pelo mesmo motor e confirma os achados. XML inválido vira dead-letter.
"""

from __future__ import annotations

import contextlib

import pytest
from sqlalchemy import text

from app.connectors.upload.load import load_nfe_files
from app.core.db import tenant_session
from app.findings.service import list_findings
from app.rules.engine import run_all
from app.rules.retention_rules import register_retention_rules
from scripts.seed_synthetic import TENANT_ID, seed

SERVICE_NFE = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
 <NFe><infNFe Id="NFe35200114200166000187550010000000123456789012">
  <ide><nNF>123</nNF><serie>1</serie><dhEmi>2026-05-10T10:00:00-03:00</dhEmi>
   <natOp>PRESTACAO DE SERVICO DE INSTALACAO</natOp></ide>
  <emit><CNPJ>14200166000187</CNPJ><xNome>Fornecedor Servicos LTDA</xNome></emit>
  <dest><CNPJ>09999999000191</CNPJ><xNome>Construtora Cliente</xNome></dest>
  <det nItem="1"><prod><cProd>SVC01</cProd><xProd>Servico de instalacao</xProd>
   <NCM>00000000</NCM><CFOP>5933</CFOP><uCom>UN</uCom><qCom>1.0000</qCom>
   <vUnCom>5000.00</vUnCom><vProd>5000.00</vProd></prod></det>
  <total><ICMSTot><vProd>5000.00</vProd><vICMS>0.00</vICMS><vIPI>0.00</vIPI>
   <vNF>5000.00</vNF></ICMSTot></total>
 </infNFe></NFe>
</nfeProc>"""


@pytest.fixture(scope="module", autouse=True)
def _register():
    with contextlib.suppress(ValueError):
        register_retention_rules()


@pytest.fixture
def seeded():
    return seed()


def test_upload_nfe_loads_canonical(seeded):
    summary = load_nfe_files(str(TENANT_ID), [("svc.xml", SERVICE_NFE.encode())])
    assert summary["invoices"] == 1
    assert summary["items"] == 1
    assert summary["dead_letters"] == 0
    with tenant_session(str(TENANT_ID)) as s:
        chave = "35200114200166000187550010000000123456789012"
        inv = s.execute(
            text("SELECT is_service, total_invoiced FROM invoice WHERE nfe_key = :k"), {"k": chave}
        ).one()
        assert inv.is_service is True
        assert inv.total_invoiced == 5000


def test_invalid_xml_goes_to_dead_letter(seeded):
    summary = load_nfe_files(str(TENANT_ID), [("ruim.xml", b"<nao>isto nao e nfe</nao>")])
    assert summary["dead_letters"] == 1
    assert summary["invoices"] == 0
    with tenant_session(str(TENANT_ID)) as s:
        n = s.execute(
            text("SELECT count(*) FROM dead_letter WHERE ref = 'ruim.xml'")
        ).scalar_one()
        assert n == 1


def test_retention_rules_fire(seeded):
    load_nfe_files(str(TENANT_ID), [("svc.xml", SERVICE_NFE.encode())])
    with tenant_session(str(TENANT_ID)) as s:
        run_all(s, str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        rules = {f.rule_id for f in list_findings(s, limit=1000)}
    assert "RET1" in rules, "INSS não retido deveria disparar"
    assert "RET2" in rules, "ISS não retido deveria disparar"


def test_reupload_is_idempotent(seeded):
    load_nfe_files(str(TENANT_ID), [("svc.xml", SERVICE_NFE.encode())])
    load_nfe_files(str(TENANT_ID), [("svc.xml", SERVICE_NFE.encode())])
    with tenant_session(str(TENANT_ID)) as s:
        chave = "35200114200166000187550010000000123456789012"
        n_inv = s.execute(
            text("SELECT count(*) FROM invoice WHERE nfe_key = :k"), {"k": chave}
        ).scalar_one()
        n_items = s.execute(
            text("SELECT count(*) FROM invoice_item ii JOIN invoice i ON i.id = ii.invoice_id"
                 " WHERE i.nfe_key = :k"), {"k": chave}
        ).scalar_one()
    assert n_inv == 1, "reupload duplicou a nota"
    assert n_items == 1, "reupload duplicou itens"
