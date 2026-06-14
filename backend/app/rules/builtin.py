"""As 6 regras do MVP (docs/regras.md §3).

Implementadas a partir da especificação. Quando o motor do PoC (Q2) chegar,
os golden tests (tests/test_rules.py) garantem paridade na refatoração.

Notas de fidelidade ao schema atual (a reconciliar com o PoC):
- R4 usa quantidade PEDIDA (purchase_order_item) como proxy de "atendida" até
  termos itens de nota; troca direta quando houver invoice_item.
- R6 conta concorrência por cotações dos mesmos insumos do pedido.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.money import Money
from app.models.findings import Severity
from app.models.sourcing import (
    BudgetItem,
    Bill,
    PurchaseOrder,
    PurchaseOrderItem,
    Quotation,
)
from app.models.tenancy import Project
from app.rules.base import EvidenceDraft, FindingDraft, RuleContext, dedup_key, register
from app.rules.references import resolve_price_reference

D = Decimal
ONE = Decimal("1")


def _state_of_order(session: Session, order: PurchaseOrder) -> str | None:
    if order.project_id:
        proj = session.get(Project, order.project_id)
        return proj.state if proj else None
    return None


# --------------------------------------------------------------------------- R1
class OverpriceRule:
    id = "R1"
    version = 1
    dimension = 1
    severity_default = Severity.HIGH
    default_params = {"threshold_pct": 0.10}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        threshold = D(str(ctx.params.get("threshold_pct", 0.10)))
        drafts: list[FindingDraft] = []
        items = session.execute(
            select(PurchaseOrderItem).where(
                PurchaseOrderItem.unit_price.is_not(None),
                or_(
                    PurchaseOrderItem.catalog_item_id.is_not(None),
                    PurchaseOrderItem.resource_code.is_not(None),
                ),
            )
        ).scalars()
        for item in items:
            order = session.get(PurchaseOrder, item.order_id)
            if order is None:
                continue
            ref = resolve_price_reference(
                session,
                str(item.catalog_item_id) if item.catalog_item_id else None,
                _state_of_order(session, order),
                item.resource_code,
            )
            if ref is None:
                continue
            unit_price = D(str(item.unit_price))
            limit = ref.value * (ONE + threshold)
            if unit_price <= limit:
                continue
            qty = D(str(item.qty)) if item.qty is not None else ONE
            exposed = (unit_price - ref.value) * qty
            drafts.append(
                FindingDraft(
                    rule_id=self.id,
                    rule_version=self.version,
                    dedup_key=dedup_key(self.id, item.id),
                    severity=self.severity_default.value,
                    exposed_amount=Money.of(exposed),
                    title=f"Sobrepreço: pago {unit_price} vs referência {ref.value}",
                    project_id=str(order.project_id) if order.project_id else None,
                    evidence=[
                        EvidenceDraft("purchase_order_item", "item_pedido", str(item.id),
                                      f"{item.raw_description}: {unit_price}/un x {qty}"),
                        EvidenceDraft("reference", ref.layer, None,
                                      f"referência {ref.value}", ref.snapshot),
                    ],
                    reference_snapshot=ref.snapshot,
                    config_snapshot={"threshold_pct": str(threshold)},
                )
            )
        return drafts


# --------------------------------------------------------------------------- R2
class LostQuoteRule:
    id = "R2"
    version = 1
    dimension = 1
    severity_default = Severity.HIGH
    default_params: dict = {}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        drafts: list[FindingDraft] = []
        items = session.execute(
            select(PurchaseOrderItem).where(
                PurchaseOrderItem.unit_price.is_not(None),
                PurchaseOrderItem.catalog_item_id.is_not(None),
            )
        ).scalars()
        for item in items:
            order = session.get(PurchaseOrder, item.order_id)
            if order is None:
                continue
            unit_price = D(str(item.unit_price))
            # cotação válida mais barata para o mesmo insumo
            q = session.execute(
                select(Quotation)
                .where(
                    Quotation.catalog_item_id == item.catalog_item_id,
                    Quotation.unit_price.is_not(None),
                    Quotation.unit_price < unit_price,
                )
                .order_by(Quotation.unit_price.asc())
                .limit(1)
            ).scalar_one_or_none()
            if q is None:
                continue
            if q.valid_until is not None and order.ordered_at is not None and q.valid_until < order.ordered_at:
                continue  # cotação expirada na data do pedido
            best = D(str(q.unit_price))
            qty = D(str(item.qty)) if item.qty is not None else ONE
            exposed = (unit_price - best) * qty
            drafts.append(
                FindingDraft(
                    rule_id=self.id,
                    rule_version=self.version,
                    dedup_key=dedup_key(self.id, item.id, q.id),
                    severity=self.severity_default.value,
                    exposed_amount=Money.of(exposed),
                    title=f"Cotação perdida: comprou {unit_price} havendo {best}",
                    project_id=str(order.project_id) if order.project_id else None,
                    evidence=[
                        EvidenceDraft("purchase_order_item", "item_pedido", str(item.id),
                                      f"{item.raw_description}: {unit_price}/un"),
                        EvidenceDraft("quotation", "cotacao_mais_barata", str(q.id),
                                      f"cotação {best}/un, validade {q.valid_until}"),
                    ],
                    config_snapshot={},
                )
            )
        return drafts


# --------------------------------------------------------------------------- R3
class SplittingRule:
    id = "R3"
    version = 1
    dimension = 5
    severity_default = Severity.MEDIUM
    default_params = {"window_days": 30, "below_pct": 0.10, "min_orders": 2, "alcada": 50000}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        window = int(ctx.params.get("window_days", 30))
        below = D(str(ctx.params.get("below_pct", 0.10)))
        min_orders = int(ctx.params.get("min_orders", 2))
        alcada = D(str(ctx.params.get("alcada", 50000)))
        lower = alcada * (ONE - below)
        drafts: list[FindingDraft] = []

        orders = list(
            session.execute(
                select(PurchaseOrder).where(
                    PurchaseOrder.total.is_not(None),
                    PurchaseOrder.creditor_id.is_not(None),
                    PurchaseOrder.ordered_at.is_not(None),
                ).order_by(PurchaseOrder.creditor_id, PurchaseOrder.ordered_at)
            ).scalars()
        )
        by_creditor: dict[str, list[PurchaseOrder]] = {}
        for o in orders:
            by_creditor.setdefault(str(o.creditor_id), []).append(o)

        for creditor_id, group in by_creditor.items():
            # janela deslizante: pedidos "logo abaixo" da alçada em <= window dias
            for i, anchor in enumerate(group):
                cluster = [
                    o for o in group[i:]
                    if o.ordered_at - anchor.ordered_at <= timedelta(days=window)
                    and lower <= D(str(o.total)) <= alcada
                ]
                if len(cluster) < min_orders:
                    continue
                total = sum((D(str(o.total)) for o in cluster), D(0))
                if total <= alcada:
                    continue
                drafts.append(
                    FindingDraft(
                        rule_id=self.id,
                        rule_version=self.version,
                        dedup_key=dedup_key(self.id, creditor_id, anchor.ordered_at.date()),
                        severity=self.severity_default.value,
                        exposed_amount=Money.of(total),
                        title=f"Fracionamento: {len(cluster)} pedidos somam {total} (alçada {alcada})",
                        project_id=str(anchor.project_id) if anchor.project_id else None,
                        evidence=[
                            EvidenceDraft("purchase_order", "pedido_fracionado", str(o.id),
                                          f"pedido {o.total} em {o.ordered_at.date()}")
                            for o in cluster
                        ],
                        config_snapshot={"window_days": window, "alcada": str(alcada),
                                         "below_pct": str(below)},
                    )
                )
                break  # um achado por credor por âncora
        return drafts


# --------------------------------------------------------------------------- R4
class QuantityOverrunRule:
    id = "R4"
    version = 1
    dimension = 1
    severity_default = Severity.MEDIUM
    default_params = {"tolerance_pct": 0.05}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        tol = D(str(ctx.params.get("tolerance_pct", 0.05)))
        drafts: list[FindingDraft] = []
        # Orçado vs medido/executado, ambos no próprio item de orçamento
        # (building-cost-estimation-items: quantity vs measuredQuantity).
        budgets = session.execute(
            select(BudgetItem).where(
                BudgetItem.qty_budgeted.is_not(None),
                BudgetItem.qty_measured.is_not(None),
                BudgetItem.qty_budgeted > 0,
            )
        ).scalars()
        for b in budgets:
            budgeted = D(str(b.qty_budgeted))
            measured = D(str(b.qty_measured))
            if measured <= budgeted * (ONE + tol):
                continue
            unit = D(str(b.unit_price_budgeted)) if b.unit_price_budgeted else D(0)
            exposed = (measured - budgeted) * unit
            drafts.append(
                FindingDraft(
                    rule_id=self.id,
                    rule_version=self.version,
                    dedup_key=dedup_key(self.id, b.id),
                    severity=self.severity_default.value,
                    exposed_amount=Money.of(exposed),
                    title=f"Estouro de quantidade: medido {measured} vs orçado {budgeted}",
                    project_id=str(b.project_id) if b.project_id else None,
                    evidence=[
                        EvidenceDraft("budget_item", "orcamento", str(b.id),
                                      f"{b.raw_description}: orçado {budgeted} {b.unit}, medido {measured}"),
                    ],
                    config_snapshot={"tolerance_pct": str(tol)},
                )
            )
        return drafts


# --------------------------------------------------------------------------- R5
class OrderToPaymentRule:
    id = "R5"
    version = 1
    dimension = 3
    severity_default = Severity.HIGH
    default_params = {"tolerance_pct": 0.02}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        tol = D(str(ctx.params.get("tolerance_pct", 0.02)))
        drafts: list[FindingDraft] = []
        bills = session.execute(
            select(Bill).where(Bill.amount.is_not(None), Bill.order_id.is_not(None))
        ).scalars()
        for bill in bills:
            order = session.get(PurchaseOrder, bill.order_id)
            if order is None or order.total is None:
                continue
            amount = D(str(bill.amount))
            total = D(str(order.total))
            if amount <= total * (ONE + tol):
                continue
            exposed = amount - total
            drafts.append(
                FindingDraft(
                    rule_id=self.id,
                    rule_version=self.version,
                    dedup_key=dedup_key(self.id, bill.id),
                    severity=self.severity_default.value,
                    exposed_amount=Money.of(exposed),
                    title=f"Pagto acima do pedido: pago {amount} vs pedido {total}",
                    project_id=str(order.project_id) if order.project_id else None,
                    evidence=[
                        EvidenceDraft("purchase_order", "pedido", str(order.id), f"pedido {total}"),
                        EvidenceDraft("bill", "pagamento", str(bill.id), f"pago {amount}"),
                    ],
                    config_snapshot={"tolerance_pct": str(tol)},
                )
            )
        return drafts


# --------------------------------------------------------------------------- R6
class NoCompetitionRule:
    id = "R6"
    version = 1
    dimension = 5
    severity_default = Severity.MEDIUM
    default_params = {"relevance": 50000, "min_quotes": 2}

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]:
        relevance = D(str(ctx.params.get("relevance", 50000)))
        min_quotes = int(ctx.params.get("min_quotes", 2))
        drafts: list[FindingDraft] = []
        orders = session.execute(
            select(PurchaseOrder).where(PurchaseOrder.total.is_not(None), PurchaseOrder.total > relevance)
        ).scalars()
        for order in orders:
            cat_ids = session.execute(
                select(PurchaseOrderItem.catalog_item_id).where(
                    PurchaseOrderItem.order_id == order.id,
                    PurchaseOrderItem.catalog_item_id.is_not(None),
                )
            ).scalars().all()
            if not cat_ids:
                continue
            distinct_creditors = session.execute(
                select(func.count(func.distinct(Quotation.creditor_id))).where(
                    Quotation.catalog_item_id.in_(cat_ids)
                )
            ).scalar_one()
            if distinct_creditors >= min_quotes:
                continue
            drafts.append(
                FindingDraft(
                    rule_id=self.id,
                    rule_version=self.version,
                    dedup_key=dedup_key(self.id, order.id),
                    severity=self.severity_default.value,
                    exposed_amount=Money.of(D(str(order.total))),  # valor sob governança
                    title=f"Sem concorrência: pedido {order.total} com {distinct_creditors} cotação(ões)",
                    project_id=str(order.project_id) if order.project_id else None,
                    evidence=[
                        EvidenceDraft("purchase_order", "pedido_sem_concorrencia", str(order.id),
                                      f"pedido {order.total}, {distinct_creditors} fornecedor(es) cotando"),
                    ],
                    config_snapshot={"relevance": str(relevance), "min_quotes": min_quotes},
                )
            )
        return drafts


def register_builtin_rules() -> None:
    for rule in (
        OverpriceRule(),
        LostQuoteRule(),
        SplittingRule(),
        QuantityOverrunRule(),
        OrderToPaymentRule(),
        NoCompetitionRule(),
    ):
        register(rule)
