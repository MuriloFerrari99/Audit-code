"""Fase Agêntica P4 — mitigação do Executor: flag por tenant + idempotência.

Usa o adapter log-only (seguro, sem efeito externo) p/ provar o fluxo de ação
sem tocar ERP/SMTP reais.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select, text

from app.core.db import admin_session, tenant_session
from app.disputes.service import list_disputes, mitigate_finding
from app.models.agentic import Dispute
from scripts.seed_synthetic import TENANT_ID, seed


def _set_auto(value: bool) -> None:
    with admin_session() as s:
        s.execute(
            text("UPDATE tenant SET auto_mitigation = :v WHERE id = :i"),
            {"v": value, "i": TENANT_ID},
        )


@pytest.fixture
def seeded():
    return seed()


def test_auto_off_keeps_draft(seeded):
    _set_auto(False)
    fid = str(uuid.uuid4())
    with tenant_session(str(TENANT_ID)) as s:
        d = mitigate_finding(s, str(TENANT_ID), finding_id=fid, reason="sobrepreço",
                             channel="erp", bill_external_id="B-1")
        assert d.status == "draft"      # sem opt-in -> nenhuma ação externa
        assert d.channel is None


def test_auto_on_blocks_via_logonly(seeded):
    _set_auto(True)
    fid = str(uuid.uuid4())
    with tenant_session(str(TENANT_ID)) as s:
        d = mitigate_finding(s, str(TENANT_ID), finding_id=fid, reason="pagamento sem lastro",
                             channel="erp", bill_external_id="B-9")
        assert d.status == "erp_blocked"
        assert d.channel == "erp"
        assert d.erp_ref.startswith("logonly:")


def test_mitigation_is_idempotent(seeded):
    _set_auto(True)
    fid = str(uuid.uuid4())
    with tenant_session(str(TENANT_ID)) as s:
        d1 = mitigate_finding(s, str(TENANT_ID), finding_id=fid, reason="x",
                              channel="erp", bill_external_id="B-7")
    with tenant_session(str(TENANT_ID)) as s:
        d2 = mitigate_finding(s, str(TENANT_ID), finding_id=fid, reason="x",
                              channel="erp", bill_external_id="B-7")
        assert str(d2.id) == str(d1.id)  # não reabre
        n = s.execute(
            select(func.count()).select_from(Dispute).where(Dispute.finding_id == fid)
        ).scalar_one()
    assert n == 1


def test_list_disputes(seeded):
    _set_auto(False)
    fid = str(uuid.uuid4())
    with tenant_session(str(TENANT_ID)) as s:
        mitigate_finding(s, str(TENANT_ID), finding_id=fid, reason="y")
    with tenant_session(str(TENANT_ID)) as s:
        assert len(list_disputes(s)) >= 1
