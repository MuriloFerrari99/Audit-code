"""Fase Agêntica P1 — CDM + OpenSquad (Extrator/Auditor/Executor) sob RLS."""

from __future__ import annotations

import contextlib

import pytest
from sqlalchemy import select, text

from app.agents.squad import (
    AuditorAgent,
    ExecutorAgent,
    ExtractorAgent,
    SquadContext,
)
from app.canonical.document import CanonicalDocument, DocumentType, SourceFormat
from app.canonical.mappers import fiscal_dict_to_canonical
from app.connectors.upload.nfe import parse_nfe
from app.core.db import tenant_session
from app.findings.service import list_findings
from app.models.agentic import AgentReasoningLog
from app.rules.builtin import register_builtin_rules
from scripts.seed_synthetic import TENANT_ID, seed

NFE = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
 <NFe><infNFe Id="NFe22222222222222222222222222222222222222222222">
  <ide><nNF>7</nNF><serie>1</serie><dhEmi>2026-05-10T10:00:00-03:00</dhEmi><natOp>VENDA</natOp></ide>
  <emit><CNPJ>14200166000187</CNPJ><xNome>Fornecedor LTDA</xNome></emit>
  <det nItem="1"><prod><cProd>CIM</cProd><xProd>Cimento CP-II</xProd><NCM>25232100</NCM>
   <CFOP>5102</CFOP><uCom>SC</uCom><qCom>100</qCom><vUnCom>30.00</vUnCom><vProd>3000.00</vProd></prod></det>
  <total><ICMSTot><vProd>3000.00</vProd><vNF>3000.00</vNF></ICMSTot></total>
 </infNFe></NFe></nfeProc>"""


@pytest.fixture(scope="module", autouse=True)
def _register():
    with contextlib.suppress(ValueError):
        register_builtin_rules()


@pytest.fixture
def seeded():
    return seed()


# ----------------------------------------------------------------- CDM puro
def test_nfe_maps_to_canonical():
    doc = fiscal_dict_to_canonical(parse_nfe(NFE.encode()), SourceFormat.NFE)
    assert isinstance(doc, CanonicalDocument)
    assert doc.document_type == DocumentType.GOODS_INVOICE
    assert doc.issuer.tax_id == "14200166000187"
    assert len(doc.items) == 1
    assert doc.items[0].code == "CIM"
    assert str(doc.total_amount) == "3000.00"
    # serialização estável (Decimal -> str)
    assert doc.to_dict()["total_amount"] == "3000.00"


# ----------------------------------------------------------------- squad + RLS
def test_extractor_writes_reasoning_log(seeded):
    ctx = SquadContext(tenant_id=str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        doc = ExtractorAgent().extract(s, ctx, "nota.xml", NFE.encode())
        assert doc.external_id.startswith("22222222")
    with tenant_session(str(TENANT_ID)) as s:
        logs = s.execute(
            select(AgentReasoningLog).where(AgentReasoningLog.run_id == ctx.run_id)
        ).scalars().all()
    assert len(logs) == 1
    assert logs[0].agent_name == "extractor"
    assert logs[0].status == "ok"


def test_auditor_runs_and_logs(seeded):
    ctx = SquadContext(tenant_id=str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        found = AuditorAgent().audit(s, ctx)
    assert isinstance(found, dict)
    with tenant_session(str(TENANT_ID)) as s:
        log = s.execute(
            select(AgentReasoningLog).where(
                AgentReasoningLog.run_id == ctx.run_id,
                AgentReasoningLog.agent_name == "auditor",
            )
        ).scalar_one()
    assert log.confidence_score is not None


def test_executor_opens_dispute_draft(seeded):
    ctx = SquadContext(tenant_id=str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        # pega um achado real p/ vincular
        from app.rules.engine import run_all
        run_all(s, str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        finding = list_findings(s, rule_id="R1", limit=1)[0]
        d = ExecutorAgent().open_dispute(
            s, ctx, finding_id=str(finding.id), reason="Sobrepreço vs mediana",
        )
        assert d.status == "draft"  # sem Port injetada -> nenhuma ação externa
    with tenant_session(str(TENANT_ID)) as s:
        n = s.execute(text("SELECT count(*) FROM dispute")).scalar_one()
        assert n >= 1
        log = s.execute(
            select(AgentReasoningLog).where(
                AgentReasoningLog.run_id == ctx.run_id,
                AgentReasoningLog.agent_name == "executor",
            )
        ).scalar_one()
        assert log.finding_id is not None
