"""Port de saída: ação no ERP (mitigação automática do Agente Executor).

CRÍTICO: ação que sai para fora (travar pagamento) é irreversível para o cliente
— implementações concretas devem exigir autorização/escopo e ser idempotentes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ErpActionResult:
    ok: bool
    external_ref: str | None = None
    detail: str | None = None


@runtime_checkable
class ErpActionPort(Protocol):
    """Adapter por ERP (Sienge, TOTVS, QuickBooks...)."""

    name: str

    def block_payment(self, *, tenant_id: str, bill_external_id: str,
                      reason: str) -> ErpActionResult:
        """Bloqueia/segura um pagamento no ERP. Idempotente por bill_external_id."""
        ...
