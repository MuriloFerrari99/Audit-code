"""Fase Agêntica P3 — SquadRunner: pipeline Extrator->Enriquecedor->Auditor."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.agents.squad import SquadRunner
from app.core.db import tenant_session
from app.models.agentic import AgentReasoningLog
from app.models.platform import DeadLetter
from scripts.seed_synthetic import TENANT_ID, seed

NFE = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
 <NFe><infNFe Id="NFe33333333333333333333333333333333333333333333">
  <ide><nNF>9</nNF><serie>1</serie><dhEmi>2026-05-10T10:00:00-03:00</dhEmi><natOp>VENDA</natOp></ide>
  <emit><CNPJ>14200166000187</CNPJ><xNome>Fornecedor LTDA</xNome></emit>
  <det nItem="1"><prod><cProd>CIM</cProd><xProd>Cimento</xProd><NCM>25232100</NCM>
   <CFOP>5102</CFOP><uCom>SC</uCom><qCom>50</qCom><vUnCom>30.00</vUnCom><vProd>1500.00</vProd></prod></det>
  <total><ICMSTot><vProd>1500.00</vProd><vNF>1500.00</vNF></ICMSTot></total>
 </infNFe></NFe></nfeProc>"""


@pytest.fixture
def seeded():
    return seed()


def test_runner_pipeline_ok(seeded):
    res = SquadRunner().run_document(str(TENANT_ID), "nota.xml", NFE.encode())
    assert res["extracted"] is True
    assert res["source_format"] == "nfe"
    assert isinstance(res["found"], dict)
    run_id = res["run_id"]
    with tenant_session(str(TENANT_ID)) as s:
        agents = set(
            s.execute(
                select(AgentReasoningLog.agent_name).where(AgentReasoningLog.run_id == run_id)
            ).scalars()
        )
    # os três passos do pipeline gravaram prontuário no mesmo run_id
    assert {"extractor", "enricher", "auditor"} <= agents


def test_runner_invalid_doc_dead_letters(seeded):
    res = SquadRunner().run_document(str(TENANT_ID), "ruim_runner.xml", b"<x>nao e nota</x>")
    assert res["extracted"] is False
    assert res["dead_letters"] >= 1
    with tenant_session(str(TENANT_ID)) as s:
        n = s.execute(
            select(func.count()).select_from(DeadLetter).where(DeadLetter.ref == "ruim_runner.xml")
        ).scalar_one()
    assert n >= 1
