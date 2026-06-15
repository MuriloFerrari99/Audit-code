"""Regras de retenção (Dimensão fiscal — diferencial INSS/ISS).

Heurística e ADVISORY: a obrigação de reter depende do tipo de serviço e do
município. Marcamos "possível retenção não aplicada" para revisão humana, com
confiança média. Calibração por tenant ajusta com o feedback.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.money import Money
from app.models.findings import Severity
from app.models.sourcing import Invoice
from app.rules.base import EvidenceDraft, FindingDraft, RuleContext, dedup_key, register

D = Decimal


def _service_invoices(session: Session, floor: Decimal):
    return session.execute(
        select(Invoice).where(
            Invoice.is_service.is_(True),
            Invoice.total_invoiced.is_not(None),
            Invoice.total_invoiced >= floor,
        )
    ).scalars()


# --------------------------------------------------------------------------- RET1
class InssNotWithheldRule:
    id = "RET1"
    version = 1
    dimension = 2
    severity_default = Severity.MEDIUM
    default_params = {"min_amount": 1000}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        floor = D(str(ctx.params.get("min_amount", 1000)))
        drafts: list[FindingDraft] = []
        for inv in _service_invoices(session, floor):
            if inv.inss_retention and D(str(inv.inss_retention)) > 0:
                continue  # reteve
            drafts.append(FindingDraft(
                rule_id=self.id, rule_version=self.version,
                dedup_key=dedup_key(self.id, inv.id),
                severity=self.severity_default.value,
                exposed_amount=Money.of(D(str(inv.total_invoiced))),
                title=f"Possível INSS não retido em serviço: NF {inv.number}",
                evidence=[EvidenceDraft("invoice", "inss_nao_retido", str(inv.id),
                                        f"NF {inv.number} (serviço {inv.total_invoiced}) sem retenção de INSS — revisar")],
                reference_snapshot={"source": "nfe.retTrib"},
                config_snapshot={"min_amount": str(floor)},
            ))
        return drafts


# --------------------------------------------------------------------------- RET2
class IssNotWithheldRule:
    id = "RET2"
    version = 1
    dimension = 2
    severity_default = Severity.MEDIUM
    default_params = {"min_amount": 1000}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        floor = D(str(ctx.params.get("min_amount", 1000)))
        drafts: list[FindingDraft] = []
        for inv in _service_invoices(session, floor):
            if inv.iss_retention and D(str(inv.iss_retention)) > 0:
                continue
            drafts.append(FindingDraft(
                rule_id=self.id, rule_version=self.version,
                dedup_key=dedup_key(self.id, inv.id),
                severity=self.severity_default.value,
                exposed_amount=Money.of(D(str(inv.total_invoiced))),
                title=f"Possível ISS não retido em serviço: NF {inv.number}",
                evidence=[EvidenceDraft("invoice", "iss_nao_retido", str(inv.id),
                                        f"NF {inv.number} (serviço {inv.total_invoiced}) sem retenção de ISS — revisar")],
                reference_snapshot={"source": "nfe.ISSQN"},
                config_snapshot={"min_amount": str(floor)},
            ))
        return drafts


def register_retention_rules() -> None:
    for rule in (InssNotWithheldRule(), IssNotWithheldRule()):
        register(rule)
