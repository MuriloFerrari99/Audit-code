"""Agente Triador (agentes.md): prioriza a fila por materialidade × severidade.

Determinístico (não fecha nem descarta achado — só ordena). Decisão é humana.
"""

from __future__ import annotations

from decimal import Decimal

from app.models.findings import Finding, Severity

_SEVERITY_WEIGHT = {
    Severity.CRITICAL.value: Decimal("4"),
    Severity.HIGH.value: Decimal("3"),
    Severity.MEDIUM.value: Decimal("2"),
    Severity.LOW.value: Decimal("1"),
}


def priority_score(finding: Finding) -> Decimal:
    amount = Decimal(str(finding.exposed_amount)) if finding.exposed_amount else Decimal("0")
    weight = _SEVERITY_WEIGHT.get(finding.severity, Decimal("1"))
    return amount * weight


def prioritize(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=priority_score, reverse=True)
