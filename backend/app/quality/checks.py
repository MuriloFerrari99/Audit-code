"""Higiene de Dados sobre o modelo canônico (Módulo A).

Lista lançamentos a checar/corrigir que (1) impedem auditoria e (2) geram
falso-positivo na origem. Roda por tenant (RLS). Espelha scripts/quality_alumbra.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.sourcing import BudgetItem, Creditor, PurchaseOrderItem, Quotation


@dataclass
class DataQualityIssue:
    code: str
    severity: str  # alta | media | baixa
    entity_type: str
    entity_id: str | None
    message: str
    action: str


def check_duplicate_creditors(session: Session) -> list[DataQualityIssue]:
    rows = session.execute(
        select(Creditor.cnpj_cpf, func.count(), func.array_agg(Creditor.source_external_id))
        .where(Creditor.cnpj_cpf.is_not(None), Creditor.cnpj_cpf != "")
        .group_by(Creditor.cnpj_cpf)
        .having(func.count() > 1)
    ).all()
    return [
        DataQualityIssue(
            "DQ6",
            "media",
            "creditor",
            cnpj,
            f"CNPJ {cnpj} com {n} cadastros (ids {ids})",
            "unificar fornecedor no Sienge",
        )
        for cnpj, n, ids in rows
    ]


def check_zero_price_quotations(session: Session) -> list[DataQualityIssue]:
    rows = session.execute(
        select(Quotation.id, Quotation.resource_code)
        .where(Quotation.unit_price.is_not(None), Quotation.unit_price <= 0)
        .limit(2000)
    ).all()
    return [
        DataQualityIssue(
            "DQ3",
            "media",
            "quotation",
            str(qid),
            f"cotação com preço R$ 0 (insumo {rc})",
            "remover/corrigir cotação placeholder no Sienge",
        )
        for qid, rc in rows
    ]


def check_budget_without_measurement(session: Session) -> list[DataQualityIssue]:
    rows = session.execute(
        select(BudgetItem.id, BudgetItem.raw_description)
        .where(
            BudgetItem.qty_budgeted.is_not(None),
            BudgetItem.qty_budgeted > 0,
            BudgetItem.qty_measured.is_(None),
        )
        .limit(2000)
    ).all()
    return [
        DataQualityIssue(
            "DQ5",
            "baixa",
            "budget_item",
            str(bid),
            f"orçamento sem medição: {desc[:40]}",
            "lançar medição no Sienge p/ habilitar auditoria de quantidade",
        )
        for bid, desc in rows
    ]


def check_items_without_code_or_price(session: Session) -> list[DataQualityIssue]:
    rows = session.execute(
        select(PurchaseOrderItem.id, PurchaseOrderItem.raw_description)
        .where(
            (PurchaseOrderItem.resource_code.is_(None))
            | (PurchaseOrderItem.unit_price.is_(None))
            | (PurchaseOrderItem.unit_price <= 0)
        )
        .limit(2000)
    ).all()
    return [
        DataQualityIssue(
            "DQ1",
            "alta",
            "purchase_order_item",
            str(iid),
            f"item sem código/preço: {desc[:40]}",
            "preencher código de insumo/preço no pedido",
        )
        for iid, desc in rows
    ]


def check_generic_resources(session: Session) -> list[DataQualityIssue]:
    rows = session.execute(
        select(
            PurchaseOrderItem.resource_code,
            func.count(),
            func.min(PurchaseOrderItem.unit_price),
            func.max(PurchaseOrderItem.unit_price),
        )
        .where(PurchaseOrderItem.resource_code.is_not(None), PurchaseOrderItem.unit_price > 0)
        .group_by(PurchaseOrderItem.resource_code)
        .having(func.count() >= 5)
    ).all()
    issues = []
    for rc, n, lo, hi in rows:
        if lo and float(hi) / float(lo) > 12:
            issues.append(
                DataQualityIssue(
                    "DQ2",
                    "media",
                    "resource",
                    str(rc),
                    f"insumo {rc} com preço {lo}–{hi} (n={n}) — cadastro mistura itens",
                    "desmembrar o código de insumo no Sienge",
                )
            )
    return issues


def run_quality(session: Session) -> dict:
    checks = [
        check_items_without_code_or_price,
        check_generic_resources,
        check_zero_price_quotations,
        check_budget_without_measurement,
        check_duplicate_creditors,
    ]
    issues: list[DataQualityIssue] = []
    for c in checks:
        issues.extend(c(session))
    by_code: dict[str, int] = {}
    for i in issues:
        by_code[i.code] = by_code.get(i.code, 0) + 1
    return {"total": len(issues), "by_code": by_code, "issues": issues}
