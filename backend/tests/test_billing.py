"""Fase 2 — cobrança: fatura mensal calculada do uso REAL de uploads.

Prova o vínculo upload -> usage_counter -> fatura: o plano corporativo
(invoice_limit=3000, overage_price=1.90) cobra excedente por nota acima do limite.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.billing.service import compute_monthly_invoice, current_period, increment_usage
from app.connectors.upload.load import load_nfe_files
from app.core.db import tenant_session
from app.models.billing import Plan, Subscription, UsageCounter
from scripts.bootstrap_plans import bootstrap_plans
from scripts.seed_synthetic import TENANT_ID, seed

NFE = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
 <NFe><infNFe Id="NFe11111111111111111111111111111111111111111111">
  <ide><nNF>1</nNF><serie>1</serie><dhEmi>2026-05-10T10:00:00-03:00</dhEmi>
   <natOp>VENDA</natOp></ide>
  <emit><CNPJ>14200166000187</CNPJ><xNome>Fornecedor LTDA</xNome></emit>
  <det nItem="1"><prod><cProd>X1</cProd><xProd>Cimento</xProd><NCM>25232100</NCM>
   <CFOP>5102</CFOP><uCom>SC</uCom><qCom>1</qCom><vUnCom>30.00</vUnCom>
   <vProd>30.00</vProd></prod></det>
  <total><ICMSTot><vProd>30.00</vProd><vNF>30.00</vNF></ICMSTot></total>
 </infNFe></NFe></nfeProc>"""


def _setup_corporate():
    seed()
    bootstrap_plans()
    with tenant_session(str(TENANT_ID)) as s:
        s.query(Subscription).delete()
        s.query(UsageCounter).delete()
        plan = s.execute(select(Plan).where(Plan.code == "corporativo")).scalar_one()
        s.add(Subscription(tenant_id=TENANT_ID, plan_id=plan.id, status="active"))


@pytest.fixture
def corporate():
    _setup_corporate()


def test_corporate_plan_seeded(corporate):
    with tenant_session(str(TENANT_ID)) as s:
        plan = s.execute(select(Plan).where(Plan.code == "corporativo")).scalar_one()
    assert plan.invoice_limit == 3000
    assert Decimal(str(plan.overage_price)) == Decimal("1.90")


def test_invoice_overage_from_usage(corporate):
    with tenant_session(str(TENANT_ID)) as s:
        increment_usage(s, str(TENANT_ID), invoices=3500)
    with tenant_session(str(TENANT_ID)) as s:
        inv = compute_monthly_invoice(s)
    assert inv["plan"]["code"] == "corporativo"
    assert inv["invoice_limit"] == 3000
    assert inv["invoices_used"] == 3500
    assert inv["overage_units"] == 500
    assert Decimal(inv["overage_amount"]) == Decimal("950")  # 500 * 1.90
    assert Decimal(inv["total"]) == Decimal("950")  # base 0 + 950


def test_no_overage_within_limit(corporate):
    with tenant_session(str(TENANT_ID)) as s:
        increment_usage(s, str(TENANT_ID), invoices=1200)
    with tenant_session(str(TENANT_ID)) as s:
        inv = compute_monthly_invoice(s)
    assert inv["overage_units"] == 0
    assert Decimal(inv["total"]) == Decimal("0")  # dentro do limite, só a base (0)


def test_upload_increments_usage(corporate):
    load_nfe_files(str(TENANT_ID), [("nfe.xml", NFE.encode())])
    with tenant_session(str(TENANT_ID)) as s:
        uc = s.execute(
            select(UsageCounter).where(UsageCounter.period == current_period())
        ).scalar_one()
    assert uc.invoices_count == 1


def test_reupload_does_not_double_count(corporate):
    load_nfe_files(str(TENANT_ID), [("nfe.xml", NFE.encode())])
    load_nfe_files(str(TENANT_ID), [("nfe.xml", NFE.encode())])  # mesma nota
    with tenant_session(str(TENANT_ID)) as s:
        uc = s.execute(
            select(UsageCounter).where(UsageCounter.period == current_period())
        ).scalar_one()
    assert uc.invoices_count == 1, "reupload da mesma nota recobrou"
