"""Fase 2 (fatia 4) — painel admin (cross-tenant) + upgrade por consumo."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.admin.service import set_tenant_plan, tenants_overview
from app.api.deps import require_platform_admin
from app.api.schemas import CurrentUser
from app.billing.service import billing_summary, increment_usage
from app.core.db import tenant_session
from app.models.billing import Subscription, UsageCounter
from scripts.bootstrap_plans import bootstrap_plans
from scripts.seed_synthetic import TENANT_ID, seed


@pytest.fixture
def base():
    seed()
    bootstrap_plans()
    with tenant_session(str(TENANT_ID)) as s:
        s.query(Subscription).delete()
        s.query(UsageCounter).delete()


def test_platform_admin_gate():
    admin = CurrentUser(user_id="1", email="a@x.com", tenant_id=None, role=None,
                        is_platform_admin=True)
    assert require_platform_admin(admin) is admin
    normal = CurrentUser(user_id="2", email="b@x.com", tenant_id="t", role="owner")
    with pytest.raises(HTTPException) as exc:
        require_platform_admin(normal)
    assert exc.value.status_code == 403


def test_set_plan_and_overview(base):
    set_tenant_plan(str(TENANT_ID), "essencial")
    res = set_tenant_plan(str(TENANT_ID), "corporativo")  # troca
    assert res["plan_code"] == "corporativo"
    with tenant_session(str(TENANT_ID)) as s:
        increment_usage(s, str(TENANT_ID), invoices=10)

    ov = tenants_overview()
    mine = [t for t in ov["tenants"] if t["tenant_id"] == str(TENANT_ID)]
    assert mine, "tenant não apareceu na visão admin"
    assert mine[0]["plan_code"] == "corporativo"
    assert mine[0]["invoices_used"] == 10


def test_set_plan_unknown_raises(base):
    with pytest.raises(ValueError):
        set_tenant_plan(str(TENANT_ID), "inexistente")


def test_upgrade_suggested_when_over_limit(base):
    set_tenant_plan(str(TENANT_ID), "essencial")  # limite 2000
    with tenant_session(str(TENANT_ID)) as s:
        increment_usage(s, str(TENANT_ID), invoices=2500)
    with tenant_session(str(TENANT_ID)) as s:
        summary = billing_summary(s)
    assert summary["plan"]["code"] == "essencial"
    assert summary["upgrade_suggested"] == "corporativo"  # limite 3000 comporta 2500


def test_no_upgrade_within_limit(base):
    set_tenant_plan(str(TENANT_ID), "corporativo")  # limite 3000
    with tenant_session(str(TENANT_ID)) as s:
        increment_usage(s, str(TENANT_ID), invoices=100)
    with tenant_session(str(TENANT_ID)) as s:
        summary = billing_summary(s)
    assert summary["upgrade_suggested"] is None
