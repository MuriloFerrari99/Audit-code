"""Port de saída: comunicação (e-mail de contestação no idioma do tenant)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class NotificationResult:
    ok: bool
    external_ref: str | None = None
    detail: str | None = None


@runtime_checkable
class NotificationPort(Protocol):
    """Adapter de envio (e-mail/SMTP, provedor transacional, webhook)."""

    name: str

    def send_dispute(self, *, tenant_id: str, to: str, subject: str,
                     body: str, locale: str) -> NotificationResult:
        """Envia a peça de contestação. Idempotência fica a cargo do chamador."""
        ...
