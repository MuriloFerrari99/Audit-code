"""Transformação raw (Sienge) -> campos canônicos (puro, testável).

Funções puras: recebem o payload bruto do Sienge e devolvem um dict de campos
canônicos. As FKs externas (supplier/building/forecastBill/creditor) ficam como
*_ext (id de origem) para o orquestrador (load.py) resolver para uuid interno.

Campos validados contra a API real da Alumbra (docs/conector-sienge.md §8b).
"""

from __future__ import annotations

from typing import Any


def _s(v: Any) -> str | None:
    return str(v) if v not in (None, "") else None


def to_company(p: dict) -> dict:
    return {"source_external_id": _s(p.get("id")), "name": p.get("name"), "cnpj": p.get("cnpj")}


def to_creditor(p: dict) -> dict:
    return {
        "source_external_id": _s(p.get("id")),
        "name": p.get("name"),
        "cnpj_cpf": p.get("cnpj") or p.get("cpf"),
    }


def to_purchase_order(p: dict) -> dict:
    return {
        "source_external_id": _s(p.get("id")),
        "total": p.get("totalAmount"),
        "status": p.get("status"),
        "ordered_at": p.get("date") or p.get("createdAt"),
        "supplier_ext": _s(p.get("supplierId")),
        "building_ext": _s(p.get("buildingId")),
        "forecast_bill_ext": _s(p.get("forecastBillId")),
        "authorized": p.get("authorized"),
    }


def to_order_item(p: dict) -> dict:
    return {
        "resource_code": _s(p.get("resourceId") or p.get("resourceCode")),
        "raw_description": p.get("resourceDescription"),
        "qty": p.get("quantity"),
        "unit_price": p.get("unitPrice"),
        "unit": p.get("unitOfMeasure"),
    }


def to_quotation_rows(p: dict) -> list[dict]:
    """Decompõe a cotação aninhada em linhas (fornecedor × insumo × preço).

    Preço fica em purchaseQuotationSuppliers[].negotiations[].negotiationItems[].
    `resource_code` = productId (ASSUNÇÃO: mesmo namespace do resourceId do item
    do pedido — validar com dado real). source_external_id composto garante dedup.
    """
    q_ext = _s(p.get("purchaseQuotationId"))
    deadline = p.get("responseDeadline")
    # mapa productId -> descrição (vem nos itens da cotação)
    desc: dict[str, str] = {}
    for it in p.get("purchaseQuotationItems") or []:
        pid = _s(it.get("productId"))
        if pid:
            desc[pid] = it.get("productDescription") or ""

    rows: list[dict] = []
    for sup in p.get("purchaseQuotationSuppliers") or []:
        sup_ext = _s(sup.get("supplierId"))
        for neg in sup.get("negotiations") or []:
            valid = neg.get("expirationDate") or deadline
            for ni in neg.get("negotiationItems") or []:
                pid = _s(ni.get("productId"))
                if pid is None or ni.get("unitPrice") is None:
                    continue
                rows.append(
                    {
                        "source_external_id": f"{q_ext}:{sup_ext}:{pid}",
                        "quotation_ext": q_ext,
                        "supplier_ext": sup_ext,
                        "resource_code": pid,
                        "unit_price": ni.get("unitPrice"),
                        "qty": ni.get("negotiatedQuantity") or ni.get("quotedQuantity"),
                        "valid_until": valid,
                        "raw_description": desc.get(pid) or "(cotação)",
                        "selected": ni.get("selectedOption"),
                    }
                )
    return rows


def to_budget_item(p: dict) -> dict:
    bid = _s(p.get("buildingId"))
    # id do item pode repetir entre obras -> chave composta obra:id
    ext = f"{bid}:{p.get('id')}" if bid else _s(p.get("id"))
    return {
        "source_external_id": ext,
        "building_ext": bid,
        "resource_code": _s(p.get("workItemId")),
        "raw_description": p.get("description"),
        "unit": p.get("unitOfMeasure"),
        "qty_budgeted": p.get("quantity"),
        "qty_measured": p.get("measuredQuantity"),
        "unit_price_budgeted": p.get("unitPrice"),
        "total_budgeted": p.get("totalPrice"),
    }


def to_invoice(p: dict) -> dict:
    """Nota fiscal (/purchase-invoices) -> canônico (dim.2 Fase A)."""
    company = _s(p.get("companyId"))
    seq = _s(p.get("sequentialNumber"))
    total = p.get("eletronicInvoiceAmount") or p.get("itemsTotalAmount")
    return {
        "source_external_id": f"{company}:{seq}" if company and seq else seq,
        "number": _s(p.get("number")),
        "series": _s(p.get("series")),
        "issued_at": p.get("issueDate"),
        "total_invoiced": total,
        "products_amount": p.get("productsAmount"),
        "ipi_tax": p.get("ipiTax"),
        "icms_st_tax": p.get("icmsStTax"),
        "consistency": _s(p.get("consistency")),
        "eletronic_invoice_id": _s(p.get("eletronicInvoiceId")),
        "supplier_ext": _s(p.get("supplierId")),
        "bill_ext": _s(p.get("billId")),
    }


def to_bill(p: dict) -> dict:
    return {
        "source_external_id": _s(p.get("id")),
        "amount": p.get("totalInvoiceAmount"),
        "creditor_ext": _s(p.get("creditorId")),
        "status": p.get("status"),
        "issued_at": p.get("issueDate"),
        "document_number": _s(p.get("documentNumber")),
        "document_identification": _s(p.get("documentIdentificationId")),
    }
