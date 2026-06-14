"""Testa os mapeadores de transformação contra payloads REAIS da API da Alumbra
(capturados na sondagem). Puro — roda sem DB nem deps externas.
"""

from __future__ import annotations

from app.connectors.sienge import transform as t

# Amostras reais (campos validados em 2026-06 contra api.sienge.com.br/alumbra).
CREDITOR = {"id": 1, "name": "SOFTPLAN PLANEJAMENTO E SISTEMAS LTDA", "cpf": None,
            "cnpj": "82.845.322/0001-04", "active": True}
COMPANY = {"id": 3, "name": "ALUMBRA EMPREENDIMENTOS", "tradeName": "", "cnpj": "00.000.000/0001-00"}
ORDER = {"id": 8649, "totalAmount": 1175.0, "status": "PENDING", "date": "2026-06-12",
         "supplierId": 1768, "buildingId": 202, "forecastBillId": 44059, "authorized": True}
ITEM = {"itemNumber": 1, "resourceId": 555, "resourceCode": "MAT-555",
        "resourceDescription": "CIMENTO CP-II 50KG", "quantity": 100.0, "unitPrice": 31.5,
        "unitOfMeasure": "SC"}
BILL = {"id": 44059, "creditorId": 1768, "totalInvoiceAmount": 1200.0, "status": "PAID",
        "issueDate": "2026-06-10", "installmentsNumber": 1}
BUDGET = {"id": 1, "buildingId": 202, "buildingName": "BRAVA GREEN - OBRA",
          "description": "LIGACOES DEFINITIVAS", "workItemId": 5001, "quantity": 100.0,
          "measuredQuantity": 130.0, "unitPrice": 90.0, "totalPrice": 9000.0, "unitOfMeasure": "m3"}


def test_creditor():
    r = t.to_creditor(CREDITOR)
    assert r["source_external_id"] == "1"
    assert r["cnpj_cpf"] == "82.845.322/0001-04"


def test_company():
    assert t.to_company(COMPANY)["source_external_id"] == "3"


def test_purchase_order_links():
    r = t.to_purchase_order(ORDER)
    assert r["total"] == 1175.0
    assert r["supplier_ext"] == "1768"
    assert r["building_ext"] == "202"
    assert r["forecast_bill_ext"] == "44059"  # ponte p/ R5 (pedido->título)
    assert r["ordered_at"] == "2026-06-12"


def test_order_item():
    r = t.to_order_item(ITEM)
    assert r["resource_code"] == "555"  # chave de comparação intra-tenant (R1/R4)
    assert r["unit_price"] == 31.5
    assert r["qty"] == 100.0


def test_bill():
    r = t.to_bill(BILL)
    assert r["source_external_id"] == "44059"
    assert r["amount"] == 1200.0
    assert r["creditor_ext"] == "1768"


def test_budget_item():
    r = t.to_budget_item(BUDGET)
    assert r["source_external_id"] == "202:1"  # chave composta obra:id
    assert r["building_ext"] == "202"
    assert r["resource_code"] == "5001"  # workItemId
    assert r["qty_budgeted"] == 100.0
    assert r["qty_measured"] == 130.0  # base da R4 (medido vs orçado)
    assert r["unit_price_budgeted"] == 90.0
