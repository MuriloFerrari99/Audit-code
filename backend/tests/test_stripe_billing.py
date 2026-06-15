"""Fase 2 (fatia 3) — provedor de pagamento (Stripe).

Testa SEM rede: verificação de assinatura do webhook + normalização de evento +
aplicação no schema (vincula/atualiza a assinatura). Criar checkout exige chave
real e não roda no CI.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest
import stripe
from sqlalchemy import select

from app.billing.providers import get_provider
from app.billing.providers.stripe_provider import StripeProvider
from app.billing.service import apply_provider_event
from app.core.db import tenant_session
from app.models.billing import Plan, Subscription
from scripts.bootstrap_plans import bootstrap_plans
from scripts.seed_synthetic import TENANT_ID, seed

SECRET = "whsec_test_secret"


def _sign(payload: bytes) -> str:
    t = int(time.time())
    signed = f"{t}.".encode() + payload
    sig = hmac.new(SECRET.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={t},v1={sig}"


def _event(payload: dict) -> bytes:
    payload.setdefault("object", "event")  # Stripe inclui o tipo do objeto no topo
    return json.dumps(payload).encode()


@pytest.fixture
def provider():
    return StripeProvider(api_key="sk_test_x", webhook_secret=SECRET)


@pytest.fixture
def subscribed():
    seed()
    bootstrap_plans()
    with tenant_session(str(TENANT_ID)) as s:
        s.query(Subscription).delete()
        plan = s.execute(select(Plan).where(Plan.code == "corporativo")).scalar_one()
        s.add(Subscription(tenant_id=TENANT_ID, plan_id=plan.id, status="incomplete"))


def test_provider_off_by_default():
    assert get_provider() is None  # billing_provider="none" no ambiente de teste


def test_invalid_signature_rejected(provider):
    payload = _event({"id": "evt_1", "type": "invoice.paid", "data": {"object": {}}})
    with pytest.raises(stripe.SignatureVerificationError):
        provider.parse_event(payload, "t=1,v1=deadbeef")


def test_checkout_completed_links_and_activates(provider, subscribed):
    payload = _event({
        "id": "evt_co",
        "type": "checkout.session.completed",
        "data": {"object": {
            "subscription": "sub_123",
            "client_reference_id": str(TENANT_ID),
            "metadata": {"tenant_id": str(TENANT_ID)},
        }},
    })
    event = provider.parse_event(payload, _sign(payload))
    assert event.subscription_ref == "sub_123"
    assert event.tenant_id == str(TENANT_ID)

    res = apply_provider_event(event)
    assert res["handled"] is True
    with tenant_session(str(TENANT_ID)) as s:
        sub = s.execute(select(Subscription)).scalar_one()
    assert sub.provider == "stripe"
    assert sub.provider_ref == "sub_123"
    assert sub.status == "active"


def test_subscription_past_due_updates_status(provider, subscribed):
    # primeiro vincula
    co = _event({"id": "e1", "type": "checkout.session.completed",
                 "data": {"object": {"subscription": "sub_9", "client_reference_id": str(TENANT_ID)}}})
    apply_provider_event(provider.parse_event(co, _sign(co)))
    # depois marca past_due
    up = _event({"id": "e2", "type": "customer.subscription.updated",
                 "data": {"object": {"id": "sub_9", "status": "past_due"}}})
    event = provider.parse_event(up, _sign(up))
    assert event.status == "past_due"
    apply_provider_event(event)
    with tenant_session(str(TENANT_ID)) as s:
        sub = s.execute(select(Subscription)).scalar_one()
    assert sub.status == "past_due"
