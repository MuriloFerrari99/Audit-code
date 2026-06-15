"""Adapters de ERP (ErpActionPort). Default SEGURO = log-only (sem efeito externo).

O adapter real (Sienge) só é selecionado por configuração explícita e exige
homologação — bloquear pagamento é irreversível para o cliente.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger
from app.ports.erp import ErpActionResult

log = get_logger("adapter.erp")


class LogOnlyErpAdapter:
    """Registra a intenção de bloqueio sem tocar o ERP. Padrão seguro."""

    name = "log_only"

    def block_payment(self, *, tenant_id: str, bill_external_id: str,
                      reason: str) -> ErpActionResult:
        log.info("erp.block_payment.logonly", tenant_id=tenant_id,
                 bill=bill_external_id, reason=reason)
        return ErpActionResult(ok=True, external_ref=f"logonly:{bill_external_id}",
                               detail="sem efeito externo (log-only)")


class SiengeErpAdapter:
    """Adapter real (gated). Requer credencial e homologação do endpoint de bloqueio."""

    name = "sienge"

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id

    def block_payment(self, *, tenant_id: str, bill_external_id: str,
                      reason: str) -> ErpActionResult:
        # Implementação real exige endpoint homologado + idempotência no ERP.
        raise NotImplementedError("SiengeErpAdapter.block_payment pendente de homologação")


def get_erp_adapter(tenant_id: str):
    """Seleciona o adapter por config. Default log-only (nunca age por acidente)."""
    provider = (get_settings().erp_provider or "log_only").lower()
    if provider == "sienge":
        return SiengeErpAdapter(tenant_id)
    return LogOnlyErpAdapter()
