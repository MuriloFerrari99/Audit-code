"""Ports (arquitetura hexagonal) — contratos entre o Core e o mundo externo.

- Driving (entrada): DocumentParser produz CDM a partir de bytes brutos.
- Driven (saída): ReferencePriceProvider (preço de mercado), ErpActionPort
  (travar pagamento), NotificationPort (e-mail de contestação).

O Core/OpenSquad depende SÓ destas interfaces; as implementações concretas vivem
em app/connectors (entrada) e app/adapters de saída — trocáveis por país/setor/ERP.
"""

from app.ports.erp import ErpActionPort, ErpActionResult
from app.ports.notification import NotificationPort, NotificationResult
from app.ports.parser import DocumentParser
from app.ports.reference import PriceReference, ReferencePriceProvider

__all__ = [
    "DocumentParser",
    "ReferencePriceProvider",
    "PriceReference",
    "ErpActionPort",
    "ErpActionResult",
    "NotificationPort",
    "NotificationResult",
]
