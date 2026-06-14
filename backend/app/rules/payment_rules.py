"""Regras da Dimensão 3 — Pagamento (Fase A, do Sienge, sem Open Finance).

P1 pagamento duplicado; P2 pagamento sem lastro. (R5/F3 já cobrem divergência
pedido/nota↔pagamento.) Conta divergente e conciliação bancária = Fase B
(Open Finance). Advisory + evidência; P1 tem confiança média (risco de FP por
parcela) — calibrável por tenant.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.money import Money
from app.models.findings import Severity
from app.models.sourcing import Bill, Invoice
from app.rules.base import EvidenceDraft, FindingDraft, RuleContext, dedup_key, register

D = Decimal


# --------------------------------------------------------------------------- P1
class DuplicatePaymentRule:
    id = "P1"
    version = 1
    dimension = 3
    severity_default = Severity.HIGH
    default_params = {"min_amount": 100}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        floor = D(str(ctx.params.get("min_amount", 100)))
        drafts: list[FindingDraft] = []
        rows = session.execute(
            select(
                Bill.creditor_id, Bill.document_number, Bill.document_identification,
                Bill.amount, func.count(), func.array_agg(Bill.source_external_id),
            )
            .where(Bill.document_number.is_not(None), Bill.amount.is_not(None),
                   Bill.amount >= floor, Bill.creditor_id.is_not(None))
            .group_by(Bill.creditor_id, Bill.document_number, Bill.document_identification, Bill.amount)
            .having(func.count() > 1)
        ).all()
        for creditor_id, doc, ident, amount, n, ext_ids in rows:
            amt = D(str(amount))
            exposed = amt * (n - 1)  # as vias extras
            drafts.append(FindingDraft(
                rule_id=self.id, rule_version=self.version,
                dedup_key=dedup_key(self.id, creditor_id, doc, ident, str(amount)),
                severity=self.severity_default.value,
                exposed_amount=Money.of(exposed),
                title=f"Pagamento possivelmente duplicado: doc {doc} x{n} ({amt} cada)",
                evidence=[EvidenceDraft("bill", "titulos_duplicados", None,
                                        f"{n} títulos {doc}/{ident} de {amt} (ids {ext_ids})")],
                config_snapshot={"min_amount": str(floor)},
            ))
        return drafts


# --------------------------------------------------------------------------- P2
class PaymentWithoutBackingRule:
    id = "P2"
    version = 1
    dimension = 3
    severity_default = Severity.MEDIUM
    default_params = {"min_amount": 1000}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        floor = D(str(ctx.params.get("min_amount", 1000)))
        with_invoice = select(Invoice.bill_external).where(Invoice.bill_external.is_not(None))
        bills = session.execute(
            select(Bill).where(
                Bill.order_id.is_(None),
                Bill.amount.is_not(None), Bill.amount >= floor,
                Bill.source_external_id.not_in(with_invoice),
            )
        ).scalars()
        drafts: list[FindingDraft] = []
        for b in bills:
            drafts.append(FindingDraft(
                rule_id=self.id, rule_version=self.version,
                dedup_key=dedup_key(self.id, b.id),
                severity=self.severity_default.value,
                exposed_amount=Money.of(D(str(b.amount))),
                title=f"Pagamento sem lastro: título {b.document_number or b.source_external_id} {b.amount}",
                evidence=[EvidenceDraft("bill", "sem_lastro", str(b.id),
                                        f"título {b.amount} sem pedido nem nota vinculados")],
                config_snapshot={"min_amount": str(floor)},
            ))
        return drafts


def register_payment_rules() -> None:
    for rule in (DuplicatePaymentRule(), PaymentWithoutBackingRule()):
        register(rule)
