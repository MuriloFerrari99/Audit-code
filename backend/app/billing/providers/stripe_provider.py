"""Provedor Stripe. Checkout (recorrente) + parsing seguro de webhook.

`parse_event` apenas verifica assinatura e normaliza — NÃO chama a rede (roda no
CI). `create_checkout` chama a API da Stripe (exige STRIPE_API_KEY + Price
configurado no painel da Stripe). Ver docs/fase-2-monetizacao.md.
"""

from __future__ import annotations

import stripe

from app.billing.providers.base import ProviderEvent
from app.core.config import get_settings

# status da assinatura Stripe -> status normalizado no nosso schema
_STATUS_MAP = {
    "active": "active",
    "trialing": "active",
    "past_due": "past_due",
    "unpaid": "past_due",
    "canceled": "canceled",
    "incomplete": "past_due",
    "incomplete_expired": "canceled",
}


class StripeProvider:
    name = "stripe"

    def __init__(self, api_key: str | None = None, webhook_secret: str | None = None) -> None:
        s = get_settings()
        self._api_key = api_key or s.stripe_api_key
        self._webhook_secret = webhook_secret or s.stripe_webhook_secret

    def create_checkout(self, *, tenant_id: str, plan_code: str, price_ref: str,
                        success_url: str, cancel_url: str, customer_ref: str | None) -> dict:
        if not self._api_key:
            raise ValueError("STRIPE_API_KEY ausente — configure o segredo do provedor")
        stripe.api_key = self._api_key
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_ref, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            customer=customer_ref or None,
            client_reference_id=tenant_id,
            metadata={"tenant_id": tenant_id, "plan_code": plan_code},
            # propaga tenant_id p/ a assinatura -> eventos futuros já vêm com ele
            subscription_data={"metadata": {"tenant_id": tenant_id, "plan_code": plan_code}},
        )
        return {"url": session.url, "ref": session.id}

    def parse_event(self, payload: bytes, signature: str | None) -> ProviderEvent:
        if not self._webhook_secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET ausente — não verifico webhook")
        event = stripe.Webhook.construct_event(payload, signature, self._webhook_secret)

        def g(obj, key, default=None):  # StripeObject (v15) não expõe .get
            try:
                return obj[key]
            except (KeyError, TypeError):
                return default

        etype = event["type"]
        obj = event["data"]["object"]
        meta = g(obj, "metadata") or {}
        sub_ref = None
        status = None
        amount = None
        tenant_id = g(meta, "tenant_id")
        if etype == "checkout.session.completed":
            sub_ref = g(obj, "subscription")
            tenant_id = tenant_id or g(obj, "client_reference_id")
            status = "active"
        elif etype.startswith("customer.subscription"):
            sub_ref = g(obj, "id")
            status = _STATUS_MAP.get(g(obj, "status", ""), g(obj, "status"))
            if etype.endswith("deleted"):
                status = "canceled"
        elif etype.startswith("invoice."):
            sub_ref = g(obj, "subscription")
            paid = g(obj, "amount_paid")
            amount = str(paid / 100) if isinstance(paid, (int, float)) else None
            status = "active" if etype in ("invoice.paid", "invoice.payment_succeeded") else "past_due"
        return ProviderEvent(
            id=g(event, "id", ""), type=etype, subscription_ref=sub_ref,
            tenant_id=tenant_id, status=status, amount=amount, raw=None,
        )
