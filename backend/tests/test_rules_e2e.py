"""E2E do motor de regras (T-094/T-171): seed -> regras -> achados -> revisão -> ledger.

Golden test do MVP: cada uma das 6 regras deve disparar sobre o cenário
sintético, com R$ exposto correto. Quando o PoC (Q2) chegar, este teste fixa a
paridade na refatoração.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import text

from app.core.db import tenant_session
from app.findings.service import list_findings, review_finding
from app.models.findings import FindingStatus
from app.rules.builtin import register_builtin_rules
from app.rules.engine import run_all
from scripts.seed_synthetic import TENANT_ID, seed


@pytest.fixture(scope="module", autouse=True)
def _register():
    try:
        register_builtin_rules()
    except ValueError:
        pass  # já registradas no processo


@pytest.fixture
def seeded():
    info = seed()
    yield info


def _by_rule(findings):
    out: dict[str, list] = {}
    for f in findings:
        out.setdefault(f.rule_id, []).append(f)
    return out


def test_all_six_rules_fire(seeded):
    with tenant_session(str(TENANT_ID)) as s:
        run_all(s, str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        findings = list_findings(s, limit=1000)
    by_rule = _by_rule(findings)
    for rid in ["R1", "R2", "R3", "R4", "R5", "R6"]:
        assert rid in by_rule, f"regra {rid} não disparou"


def test_exposed_amounts(seeded):
    with tenant_session(str(TENANT_ID)) as s:
        run_all(s, str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        by_rule = _by_rule(list_findings(s, limit=1000))

    def amounts(rid):
        return {f.exposed_amount for f in by_rule.get(rid, [])}

    assert Decimal("1000.0000") in amounts("R1")  # (40-30)*100 cimento
    assert Decimal("800.0000") in amounts("R2")   # (50-42)*100 aço
    assert Decimal("2700.0000") in amounts("R4")  # (130-100)*90 brita (medido vs orçado)
    assert Decimal("1000.0000") in amounts("R5")  # 11000-10000


def test_idempotent_rerun(seeded):
    with tenant_session(str(TENANT_ID)) as s:
        run_all(s, str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        n1 = len(list_findings(s, limit=1000))
    with tenant_session(str(TENANT_ID)) as s:
        run_all(s, str(TENANT_ID))  # segundo run
    with tenant_session(str(TENANT_ID)) as s:
        n2 = len(list_findings(s, limit=1000))
    assert n1 == n2, "re-run duplicou achados (dedup falhou)"


def test_review_creates_ledger(seeded):
    with tenant_session(str(TENANT_ID)) as s:
        run_all(s, str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        finding = list_findings(s, rule_id="R1", limit=1)[0]
        fid = str(finding.id)
        expected = finding.exposed_amount
        review_finding(s, str(TENANT_ID), fid, "accept", "tester@cliente.com")
    with tenant_session(str(TENANT_ID)) as s:
        status = s.execute(text("SELECT status FROM finding WHERE id = :i"), {"i": fid}).scalar_one()
        assert status == FindingStatus.ACCEPTED.value
        validated = s.execute(
            text("SELECT validated_amount FROM value_ledger WHERE finding_id = :i"), {"i": fid}
        ).scalar_one()
        assert validated == expected  # exposto validado entra no ledger


def test_human_decision_is_sticky(seeded):
    """Após aceitar, um novo run NÃO pode reverter o status para OPEN (ADR-02)."""
    with tenant_session(str(TENANT_ID)) as s:
        run_all(s, str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        finding = list_findings(s, rule_id="R5", limit=1)[0]
        fid = str(finding.id)
        review_finding(s, str(TENANT_ID), fid, "accept", "tester@cliente.com")
    with tenant_session(str(TENANT_ID)) as s:
        run_all(s, str(TENANT_ID))
    with tenant_session(str(TENANT_ID)) as s:
        status = s.execute(text("SELECT status FROM finding WHERE id = :i"), {"i": fid}).scalar_one()
        assert status == FindingStatus.ACCEPTED.value
