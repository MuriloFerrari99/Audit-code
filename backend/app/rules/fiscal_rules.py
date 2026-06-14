"""Regras da Dimensão 2 — Fiscal / Documento (Fase A, sem certificado).

Usa a nota que já está no Sienge. Advisory + evidência (nº/data/valor da nota).
F1 só dispara quando há vínculo nota↔pedido (senão não acusa — evita falso-positivo).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.money import Money
from app.models.findings import Severity
from app.models.sourcing import Bill, Invoice, PurchaseOrder
from app.rules.base import EvidenceDraft, FindingDraft, RuleContext, dedup_key, register

D = Decimal
ONE = Decimal("1")


# --------------------------------------------------------------------------- F1
class InvoiceVsOrderRule:
    id = "F1"
    version = 1
    dimension = 2
    severity_default = Severity.HIGH
    default_params = {"tolerance_pct": 0.02}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        tol = D(str(ctx.params.get("tolerance_pct", 0.02)))
        drafts: list[FindingDraft] = []
        invs = session.execute(
            select(Invoice).where(Invoice.order_id.is_not(None),
                                  Invoice.total_invoiced.is_not(None))
        ).scalars()
        for inv in invs:
            order = session.get(PurchaseOrder, inv.order_id)
            if order is None or order.total is None:
                continue
            nota = D(str(inv.total_invoiced))
            ped = D(str(order.total))
            if ped <= 0 or nota <= ped * (ONE + tol):
                continue
            drafts.append(FindingDraft(
                rule_id=self.id, rule_version=self.version,
                dedup_key=dedup_key(self.id, inv.id),
                severity=self.severity_default.value,
                exposed_amount=Money.of(nota - ped),
                title=f"Nota acima do pedido: NF {inv.number} {nota} vs pedido {ped}",
                project_id=str(order.project_id) if order.project_id else None,
                evidence=[
                    EvidenceDraft("purchase_order", "pedido", str(order.id), f"pedido {ped}"),
                    EvidenceDraft("invoice", "nota", str(inv.id), f"NF {inv.number} valor {nota}"),
                ],
                config_snapshot={"tolerance_pct": str(tol)},
            ))
        return drafts


# --------------------------------------------------------------------------- F2
class InconsistentInvoiceRule:
    id = "F2"
    version = 1
    dimension = 2
    severity_default = Severity.MEDIUM
    default_params: dict = {}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        drafts: list[FindingDraft] = []
        invs = session.execute(
            select(Invoice).where(Invoice.consistency == "N")
        ).scalars()
        for inv in invs:
            amount = D(str(inv.total_invoiced)) if inv.total_invoiced is not None else D(0)
            drafts.append(FindingDraft(
                rule_id=self.id, rule_version=self.version,
                dedup_key=dedup_key(self.id, inv.id),
                severity=self.severity_default.value,
                exposed_amount=Money.of(amount),
                title=f"Nota marcada como inconsistente: NF {inv.number}",
                evidence=[EvidenceDraft("invoice", "nota_inconsistente", str(inv.id),
                                        f"NF {inv.number} (consistency=N no Sienge), valor {amount}")],
                reference_snapshot={"source": "sienge.consistency"},
            ))
        return drafts


# --------------------------------------------------------------------------- F3
class InvoiceVsPaymentRule:
    id = "F3"
    version = 1
    dimension = 2
    severity_default = Severity.HIGH
    default_params = {"tolerance_pct": 0.02}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        tol = D(str(ctx.params.get("tolerance_pct", 0.02)))
        drafts: list[FindingDraft] = []
        invs = session.execute(
            select(Invoice).where(Invoice.bill_external.is_not(None),
                                  Invoice.total_invoiced.is_not(None))
        ).scalars()
        for inv in invs:
            bill = session.execute(
                select(Bill).where(Bill.source == "sienge",
                                   Bill.source_external_id == inv.bill_external)
            ).scalar_one_or_none()
            if bill is None or bill.amount is None:
                continue
            nota = D(str(inv.total_invoiced))
            pago = D(str(bill.amount))
            if nota <= 0 or pago <= nota * (ONE + tol):
                continue
            drafts.append(FindingDraft(
                rule_id=self.id, rule_version=self.version,
                dedup_key=dedup_key(self.id, inv.id),
                severity=self.severity_default.value,
                exposed_amount=Money.of(pago - nota),
                title=f"Pagamento acima da nota: título {pago} vs NF {inv.number} {nota}",
                evidence=[
                    EvidenceDraft("invoice", "nota", str(inv.id), f"NF {inv.number} {nota}"),
                    EvidenceDraft("bill", "pagamento", str(bill.id), f"título {pago}"),
                ],
                config_snapshot={"tolerance_pct": str(tol)},
            ))
        return drafts


def register_fiscal_rules() -> None:
    for rule in (InvoiceVsOrderRule(), InconsistentInvoiceRule(), InvoiceVsPaymentRule()):
        register(rule)
