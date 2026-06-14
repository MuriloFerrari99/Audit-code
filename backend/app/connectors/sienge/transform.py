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


def to_bill(p: dict) -> dict:
    return {
        "source_external_id": _s(p.get("id")),
        "amount": p.get("totalInvoiceAmount"),
        "creditor_ext": _s(p.get("creditorId")),
        "status": p.get("status"),
        "issued_at": p.get("issueDate"),
    }
