"""Contrato do provedor de pagamento (agnóstico)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ProviderEvent:
    """Evento de webhook normalizado (independente do provedor)."""

    id: str
    type: str  # ex.: invoice.paid, customer.subscription.updated/deleted
    subscription_ref: str | None = None
    tenant_id: str | None = None  # quando o evento carrega o nosso tenant (metadata/ref)
    status: str | None = None  # status normalizado da assinatura, quando aplicável
    amount: str | None = None
    raw: dict | None = None


class BillingProvider(Protocol):
    name: str

    def create_checkout(self, *, tenant_id: str, plan_code: str, price_ref: str,
                        success_url: str, cancel_url: str, customer_ref: str | None) -> dict:
        """Cria uma sessão de checkout e devolve {url, ref}. Faz chamada de rede."""
        ...

    def parse_event(self, payload: bytes, signature: str | None) -> ProviderEvent:
        """Verifica a assinatura do webhook e normaliza o evento. SEM rede."""
        ...
