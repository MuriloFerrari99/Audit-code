"""Fase 2 (fatia 2) — extrato de gainshare.

Prova: base = Σ validated_amount de achados ACEITOS de regras elegíveis;
governança (R3/R6) NÃO entra; gainshare = base × pct do plano; materialização
em billing_event é idempotente.
"""

from __future__ import annotations

import contextlib
from decimal import Decimal

import pytest
from sqlalchemy import select, text, update

from app.billing.service import compute_gainshare, issue_statement
from app.core.db import tenant_session
from app.findings.service import list_findings, review_finding
from app.models.billing import BillingEvent, Plan, Subscription
from app.rules.builtin import register_builtin_rules
from app.rules.engine import run_all
from scripts.bootstrap_plans import bootstrap_plans
from scripts.seed_synthetic import TENANT_ID, seed


@pytest.fixture(scope="module", autouse=True)
def _register():
    with contextlib.suppress(ValueError):
        register_builtin_rules()


@pytest.fixture
def setup():
    seed()
    bootstrap_plans()
    with tenant_session(str(TENANT_ID)) as s:
        s.query(Subscription).delete()
        s.query(BillingEvent).delete()
        plan = s.execute(select(Plan).where(Plan.code == "corporativo")).scalar_one()
        # define um % de gainshare p/ testar o cálculo (decisão comercial real fica c/ o founder)
        s.execute(update(Plan).where(Plan.id == plan.id).values(gainshare_pct=Decimal("0.20")))
        s.add(Subscription(tenant_id=TENANT_ID, plan_id=plan.id, status="active"))
    with tenant_session(str(TENANT_ID)) as s:
        run_all(s, str(TENANT_ID))


def test_governance_excluded_from_gainshare(setup):
    # aceita um achado elegível (R1) e um de governança (R6); só R1 entra na base
    with tenant_session(str(TENANT_ID)) as s:
        r1 = list_findings(s, rule_id="R1", limit=1)[0]
        r1_amount = Decimal(str(r1.exposed_amount))
        review_finding(s, str(TENANT_ID), str(r1.id), "accept", "tester@x.com")
        r6 = list_findings(s, rule_id="R6", limit=1)[0]
        review_finding(s, str(TENANT_ID), str(r6.id), "accept", "tester@x.com")
    with tenant_session(str(TENANT_ID)) as s:
        gs = compute_gainshare(s)
    assert "R1" in gs["by_rule"]
    assert "R6" not in gs["by_rule"], "governança não pode entrar na base de gainshare"
    assert Decimal(gs["base"]) == r1_amount
    assert Decimal(gs["gainshare_amount"]) == r1_amount * Decimal("0.20")


def test_issue_statement_is_idempotent(setup):
    with tenant_session(str(TENANT_ID)) as s:
        r1 = list_findings(s, rule_id="R1", limit=1)[0]
        review_finding(s, str(TENANT_ID), str(r1.id), "accept", "tester@x.com")
    with tenant_session(str(TENANT_ID)) as s:
        issue_statement(s, str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        issue_statement(s, str(TENANT_ID))  # 2ª vez não duplica
    with tenant_session(str(TENANT_ID)) as s:
        n = s.execute(text("SELECT count(*) FROM billing_event")).scalar_one()
        kinds = set(s.execute(select(BillingEvent.kind)).scalars())
    assert n == 2, "deveria haver exatamente 1 base + 1 gainshare"
    assert kinds == {"base", "gainshare"}
