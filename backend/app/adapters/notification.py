"""Adapters de notificação (NotificationPort). Default SEGURO = log-only."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger
from app.ports.notification import NotificationResult

log = get_logger("adapter.notification")


class LogOnlyNotifier:
    """Registra o e-mail de contestação sem enviar. Padrão seguro."""

    name = "log_only"

    def send_dispute(self, *, tenant_id: str, to: str, subject: str,
                     body: str, locale: str) -> NotificationResult:
        log.info("notify.dispute.logonly", tenant_id=tenant_id, to=to, subject=subject)
        return NotificationResult(ok=True, external_ref="logonly",
                                  detail="sem envio real (log-only)")


class SmtpNotifier:
    """Adapter SMTP real (gated). Requer host/credencial configurados."""

    name = "smtp"

    def send_dispute(self, *, tenant_id: str, to: str, subject: str,
                     body: str, locale: str) -> NotificationResult:
        raise NotImplementedError("SmtpNotifier pendente de configuração de SMTP")


def get_notifier(tenant_id: str):
    provider = (get_settings().notifier_provider or "log_only").lower()
    if provider == "smtp":
        return SmtpNotifier()
    return LogOnlyNotifier()
