"""Provedores de pagamento (adapter). Isola o SDK do core — trocar/adicionar
provedor não toca regras nem cobrança. Hoje: Stripe."""

from __future__ import annotations

from app.billing.providers.base import BillingProvider, ProviderEvent
from app.core.config import get_settings


def get_provider() -> BillingProvider | None:
    """Provedor configurado (settings.billing_provider). None se desligado."""
    name = (get_settings().billing_provider or "none").lower()
    if name == "stripe":
        from app.billing.providers.stripe_provider import StripeProvider

        return StripeProvider()
    return None


__all__ = ["BillingProvider", "ProviderEvent", "get_provider"]
