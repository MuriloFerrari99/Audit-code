"""Fase Agêntica P7 — auditoria event-driven: upload publica, worker drena."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.agents.squad.events import AUDIT_EVENT, drain_audit_outbox
from app.connectors.upload.load import load_nfe_files
from app.core.db import tenant_session
from app.models.agentic import AgentReasoningLog
from app.models.platform import OutboxEvent
from scripts.seed_synthetic import TENANT_ID, seed

NFE = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
 <NFe><infNFe Id="NFe55555555555555555555555555555555555555555555">
  <ide><nNF>21</nNF><serie>1</serie><dhEmi>2026-05-10T10:00:00-03:00</dhEmi><natOp>VENDA</natOp></ide>
  <emit><CNPJ>14200166000187</CNPJ><xNome>Fornecedor LTDA</xNome></emit>
  <det nItem="1"><prod><cProd>CIM</cProd><xProd>Cimento</xProd><NCM>25232100</NCM><CFOP>5102</CFOP>
   <uCom>SC</uCom><qCom>10</qCom><vUnCom>30.00</vUnCom><vProd>300.00</vProd></prod></det>
  <total><ICMSTot><vProd>300.00</vProd><vNF>300.00</vNF></ICMSTot></total>
 </infNFe></NFe></nfeProc>"""


@pytest.fixture
def seeded():
    return seed()


def _pending(s) -> int:
    return s.execute(
        select(func.count()).select_from(OutboxEvent).where(
            OutboxEvent.entity_type == AUDIT_EVENT, OutboxEvent.processed_at.is_(None)
        )
    ).scalar_one()


def test_upload_publishes_audit_event(seeded):
    load_nfe_files(str(TENANT_ID), [("nota.xml", NFE.encode())])  # emit_event=True (default)
    with tenant_session(str(TENANT_ID)) as s:
        assert _pending(s) >= 1


def test_drain_runs_auditor_and_marks_processed(seeded):
    load_nfe_files(str(TENANT_ID), [("nota.xml", NFE.encode())])
    with tenant_session(str(TENANT_ID)) as s:
        res = drain_audit_outbox(s, str(TENANT_ID))
    assert res["processed"] >= 1
    with tenant_session(str(TENANT_ID)) as s:
        assert _pending(s) == 0  # tudo processado
        log = s.execute(
            select(AgentReasoningLog).where(
                AgentReasoningLog.run_id == res["run_id"],
                AgentReasoningLog.agent_name == "auditor",
            )
        ).scalar_one()
        assert log is not None


def test_drain_noop_when_empty(seeded):
    with tenant_session(str(TENANT_ID)) as s:
        # drena qualquer pendência de cargas anteriores deste módulo
        drain_audit_outbox(s, str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        res = drain_audit_outbox(s, str(TENANT_ID))
    assert res == {"processed": 0, "found": {}}
