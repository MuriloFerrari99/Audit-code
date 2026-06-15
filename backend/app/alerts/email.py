"""Alertas por e-mail (E15, T-150/T-151). WhatsApp fica para a Fase 1.

Provedor abstrato; SMTP em prod, console em dev. Disparo por severidade/
materialidade do achado.
"""

from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from decimal import Decimal
from email.message import EmailMessage
from typing import Protocol

from app.core.logging import get_logger
from app.models.findings import Finding, Severity

log = get_logger("alerts.email")

ALERT_SEVERITIES = {Severity.HIGH.value, Severity.CRITICAL.value}
ALERT_MIN_AMOUNT = Decimal("1000")


class EmailProvider(Protocol):
    def send(self, to: list[str], subject: str, body: str) -> None: ...


class ConsoleEmailProvider:
    def send(self, to: list[str], subject: str, body: str) -> None:
        log.info("alert.email.console", to=to, subject=subject, body=body[:500])


@dataclass
class SMTPEmailProvider:
    host: str
    port: int
    user: str | None
    password: str | None
    sender: str

    def send(self, to: list[str], subject: str, body: str) -> None:  # pragma: no cover
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(self.host, self.port) as smtp:
            smtp.starttls()
            if self.user:
                smtp.login(self.user, self.password or "")
            smtp.send_message(msg)


def get_email_provider() -> EmailProvider:
    host = os.environ.get("SMTP_HOST")
    if not host:
        return ConsoleEmailProvider()
    return SMTPEmailProvider(
        host=host,
        port=int(os.environ.get("SMTP_PORT", "587")),
        user=os.environ.get("SMTP_USER"),
        password=os.environ.get("SMTP_PASSWORD"),
        sender=os.environ.get("ALERT_FROM", "alertas@exemplo.com"),
    )


def should_alert(finding: Finding) -> bool:
    if finding.severity in ALERT_SEVERITIES:
        return True
    return bool(
        finding.exposed_amount is not None
        and Decimal(str(finding.exposed_amount)) >= ALERT_MIN_AMOUNT
    )


def alert_for_finding(
    finding: Finding, recipients: list[str], provider: EmailProvider | None = None
) -> bool:
    if not should_alert(finding):
        return False
    provider = provider or get_email_provider()
    provider.send(
        recipients,
        subject=f"[Auditoria] {finding.severity.upper()}: {finding.title}",
        body=(
            f"Achado {finding.rule_id} — {finding.title}\n"
            f"R$ exposto: {finding.exposed_amount}\n"
            f"Severidade: {finding.severity}\n"
            f"Acesse o painel para revisar (aceitar/descartar/escalar)."
        ),
    )
    return True
