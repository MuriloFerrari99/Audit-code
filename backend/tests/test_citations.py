"""Fase Agêntica P5 — base legal (legal_citations) anexada aos achados fiscais."""

from __future__ import annotations

import contextlib

import pytest

from app.connectors.upload.load import load_nfe_files
from app.core.db import tenant_session
from app.findings.service import list_findings
from app.rules.citations import citations_for
from app.rules.engine import run_all
from app.rules.retention_rules import register_retention_rules
from scripts.seed_synthetic import TENANT_ID, seed

SERVICE_NFE = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
 <NFe><infNFe Id="NFe44444444444444444444444444444444444444444444">
  <ide><nNF>15</nNF><serie>1</serie><dhEmi>2026-05-10T10:00:00-03:00</dhEmi>
   <natOp>PRESTACAO DE SERVICO</natOp></ide>
  <emit><CNPJ>14200166000187</CNPJ><xNome>Servicos LTDA</xNome></emit>
  <det nItem="1"><prod><cProd>SVC</cProd><xProd>Servico</xProd><NCM>00</NCM><CFOP>5933</CFOP>
   <uCom>UN</uCom><qCom>1</qCom><vUnCom>9000.00</vUnCom><vProd>9000.00</vProd></prod></det>
  <total><ICMSTot><vProd>9000.00</vProd><vNF>9000.00</vNF></ICMSTot></total>
 </infNFe></NFe></nfeProc>"""


@pytest.fixture(scope="module", autouse=True)
def _register():
    with contextlib.suppress(ValueError):
        register_retention_rules()


@pytest.fixture
def seeded():
    return seed()


def test_citations_registry():
    assert citations_for("RET1")  # INSS
    assert citations_for("RET2")  # ISS
    assert citations_for("R1") is None  # sobrepreço não tem citação fiscal


def test_finding_carries_legal_citations(seeded):
    load_nfe_files(str(TENANT_ID), [("svc.xml", SERVICE_NFE.encode())])
    with tenant_session(str(TENANT_ID)) as s:
        run_all(s, str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        ret = list_findings(s, rule_id="RET1", limit=1)
    assert ret, "RET1 deveria ter disparado"
    cites = ret[0].legal_citations
    assert cites and any("INSS" in c or "971" in c for c in cites)
