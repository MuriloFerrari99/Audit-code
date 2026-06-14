"""Carga canônica do Sienge (raw -> entidades canônicas) com resolução de FK.

Roda no container (precisa de DB + HTTP). Resolve:
- supplierId -> creditor.id
- buildingId -> project.id (cria obra stub se não existir; company_id fica nulo)
- forecastBillId (no pedido) -> bill.order_id (ponte pedido↔título para R5)

resource_code (resourceId do Sienge) vira a chave de comparação intra-tenant
(R1/R4) sem depender do casamento de catálogo (ML).
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal

from sqlalchemy import select

from app.connectors.base import EntityKind, PullCursor
from app.connectors.sienge import transform as T
from app.connectors.sienge.connector import SiengeConnector
from app.core.db import tenant_session
from app.core.logging import get_logger
from app.models.platform import DeadLetter
from app.models.sourcing import (
    Bill,
    BudgetItem,
    Creditor,
    Invoice,
    PurchaseOrder,
    PurchaseOrderItem,
    Quotation,
)
from app.models.tenancy import Project

log = get_logger("connector.sienge.load")


def _hash(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()


def _dec(v):
    return Decimal(str(v)) if v is not None else None


def load_canonical(
    connector: SiengeConnector, tenant_id: str, max_orders: int | None = None
) -> dict[str, int]:
    """Carrega o canônico. max_orders limita a 1ª carga (a base tem milhares de
    pedidos, cada um com um sub-call de itens)."""
    connector.authenticate()
    summary = {"creditor": 0, "purchase_order": 0, "purchase_order_item": 0,
               "bill": 0, "budget_item": 0, "quotation": 0, "invoice": 0, "dead_letters": 0}

    with tenant_session(tenant_id) as s:
        # 1) Credores
        creditor_map: dict[str, str] = {}
        for raw in connector.pull(EntityKind.CREDITOR, PullCursor()):
            f = T.to_creditor(raw.payload)
            ext = f["source_external_id"]
            obj = s.execute(
                select(Creditor).where(Creditor.source == "sienge", Creditor.source_external_id == ext)
            ).scalar_one_or_none()
            if obj is None:
                obj = Creditor(tenant_id=tenant_id, source="sienge", source_external_id=ext,
                               name=f["name"] or "(sem nome)", cnpj_cpf=f["cnpj_cpf"],
                               content_hash=_hash(f))
                s.add(obj)
                s.flush()
                summary["creditor"] += 1
            creditor_map[ext] = str(obj.id)

        # 2) Obras (stub por buildingId) + 3) Pedidos + itens
        project_map: dict[str, str] = {}
        forecast_to_order: dict[str, str] = {}

        def get_project(building_ext: str | None) -> str | None:
            if not building_ext:
                return None
            if building_ext in project_map:
                return project_map[building_ext]
            proj = s.execute(
                select(Project).where(Project.external_code == building_ext)
            ).scalar_one_or_none()
            if proj is None:
                proj = Project(tenant_id=tenant_id, name=f"Obra {building_ext}",
                               external_code=building_ext)
                s.add(proj)
                s.flush()
            project_map[building_ext] = str(proj.id)
            return str(proj.id)

        processed_orders = 0
        for raw in connector.pull(EntityKind.PURCHASE_ORDER, PullCursor()):
            if max_orders is not None and processed_orders >= max_orders:
                break
            processed_orders += 1
            f = T.to_purchase_order(raw.payload)
            ext = f["source_external_id"]
            order = s.execute(
                select(PurchaseOrder).where(PurchaseOrder.source == "sienge",
                                            PurchaseOrder.source_external_id == ext)
            ).scalar_one_or_none()
            project_id = get_project(f["building_ext"])
            creditor_id = creditor_map.get(f["supplier_ext"] or "")
            if order is None:
                order = PurchaseOrder(tenant_id=tenant_id, source="sienge", source_external_id=ext,
                                      content_hash=_hash(f))
                s.add(order)
                summary["purchase_order"] += 1
            order.total = _dec(f["total"])
            order.status = f["status"]
            order.ordered_at = _parse_dt(f["ordered_at"])
            order.project_id = project_id
            order.creditor_id = creditor_id
            s.flush()
            if f["forecast_bill_ext"]:
                forecast_to_order[f["forecast_bill_ext"]] = str(order.id)

            # itens (sub-recurso)
            try:
                items = connector.pull_order_items(ext)
            except Exception as e:  # não derruba o batch (ADR-15) — mas NÃO em silêncio (A-3)
                log.warning("load.items.error", order=ext, error=str(e))
                s.add(DeadLetter(tenant_id=tenant_id, source="sienge",
                                 entity_type="purchase_order_item", ref=ext,
                                 reason=f"falha ao puxar itens: {e}"[:500]))
                summary["dead_letters"] += 1
                items = []
            for it in items:
                fi = T.to_order_item(it)
                key = f"{ext}:{it.get('itemNumber') or fi['resource_code']}"
                exists = s.execute(
                    select(PurchaseOrderItem).where(
                        PurchaseOrderItem.order_id == order.id,
                        PurchaseOrderItem.resource_code == fi["resource_code"],
                    )
                ).scalar_one_or_none()
                if exists is None:
                    s.add(PurchaseOrderItem(
                        tenant_id=tenant_id, order_id=order.id,
                        resource_code=fi["resource_code"],
                        raw_description=fi["raw_description"] or "(sem descrição)",
                        qty=_dec(fi["qty"]), unit_price=_dec(fi["unit_price"]), unit=fi["unit"],
                    ))
                    summary["purchase_order_item"] += 1

        # 3b) Orçamento (building-cost-estimation-items): orçado vs medido (R4)
        for raw in connector.pull(EntityKind.BUDGET_ITEM, PullCursor()):
            f = T.to_budget_item(raw.payload)
            ext = f["source_external_id"]
            if not ext:
                continue
            b = s.execute(
                select(BudgetItem).where(BudgetItem.source == "sienge",
                                         BudgetItem.source_external_id == ext)
            ).scalar_one_or_none()
            if b is None:
                b = BudgetItem(tenant_id=tenant_id, source="sienge", source_external_id=ext,
                               raw_description=f["raw_description"] or "(sem descrição)",
                               content_hash=_hash(f))
                s.add(b)
                summary["budget_item"] += 1
            b.project_id = get_project(f["building_ext"])
            b.resource_code = f["resource_code"]
            b.unit = f["unit"]
            b.qty_budgeted = _dec(f["qty_budgeted"])
            b.qty_measured = _dec(f["qty_measured"])
            b.unit_price_budgeted = _dec(f["unit_price_budgeted"])
            b.total_budgeted = _dec(f["total_budgeted"])

        # 4) Títulos (resolve credor + vínculo com pedido via forecastBill)
        for raw in connector.pull(EntityKind.BILL, PullCursor()):
            f = T.to_bill(raw.payload)
            ext = f["source_external_id"]
            bill = s.execute(
                select(Bill).where(Bill.source == "sienge", Bill.source_external_id == ext)
            ).scalar_one_or_none()
            if bill is None:
                bill = Bill(tenant_id=tenant_id, source="sienge", source_external_id=ext,
                            content_hash=_hash(f))
                s.add(bill)
                summary["bill"] += 1
            bill.amount = _dec(f["amount"])
            bill.status = f["status"]
            bill.document_number = f.get("document_number")
            bill.document_identification = f.get("document_identification")
            bill.creditor_id = creditor_map.get(f["creditor_ext"] or "")
            bill.order_id = forecast_to_order.get(ext)

        # 5) Cotações (decompostas: fornecedor × insumo × preço) — R2/R6
        for raw in connector.pull(EntityKind.QUOTATION, PullCursor()):
            for r in T.to_quotation_rows(raw.payload):
                ext = r["source_external_id"]
                if not ext:
                    continue
                q = s.execute(
                    select(Quotation).where(Quotation.source == "sienge",
                                            Quotation.source_external_id == ext)
                ).scalar_one_or_none()
                if q is None:
                    q = Quotation(tenant_id=tenant_id, source="sienge", source_external_id=ext,
                                  raw_description=r["raw_description"], content_hash=_hash(r))
                    s.add(q)
                    summary["quotation"] += 1
                q.resource_code = r["resource_code"]
                q.unit_price = _dec(r["unit_price"])
                q.qty = _dec(r["qty"])
                q.valid_until = _parse_dt(r["valid_until"])
                q.creditor_id = creditor_map.get(r["supplier_ext"] or "")

        # 6) Notas fiscais (dim.2 Fase A) — vínculo ao pedido via bill compartilhado
        for raw in connector.pull(EntityKind.INVOICE, PullCursor()):
            f = T.to_invoice(raw.payload)
            ext = f["source_external_id"]
            if not ext:
                continue
            inv = s.execute(
                select(Invoice).where(Invoice.source == "sienge", Invoice.source_external_id == ext)
            ).scalar_one_or_none()
            if inv is None:
                inv = Invoice(tenant_id=tenant_id, source="sienge", source_external_id=ext,
                              content_hash=_hash(f))
                s.add(inv)
                summary["invoice"] += 1
            inv.number = f["number"]
            inv.series = f["series"]
            inv.issued_at = _parse_dt(f["issued_at"])
            inv.total_invoiced = _dec(f["total_invoiced"])
            inv.products_amount = _dec(f["products_amount"])
            inv.ipi_tax = _dec(f["ipi_tax"])
            inv.icms_st_tax = _dec(f["icms_st_tax"])
            inv.consistency = f["consistency"]
            inv.eletronic_invoice_id = f["eletronic_invoice_id"]
            inv.creditor_id = creditor_map.get(f["supplier_ext"] or "")
            inv.bill_external = f["bill_ext"]
            # vínculo ao pedido (best-effort): nota e pedido compartilham o título
            inv.order_id = forecast_to_order.get(f["bill_ext"]) if f["bill_ext"] else None

    log.info("load.canonical.done", **summary)
    return summary


def _parse_dt(value):
    from app.connectors.sienge.connector import _dt
    return _dt(value)
