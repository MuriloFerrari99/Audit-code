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


QUOTATION = {
    "purchaseQuotationId": 555,
    "responseDeadline": "2026-06-01",
    "purchaseQuotationItems": [{"purchaseQuotationItemId": 1, "productId": 7975,
                               "productDescription": "VERGALHAO 10MM"}],
    "purchaseQuotationSuppliers": [
        {"supplierId": 1768, "negotiations": [
            {"negotiationId": 1, "sellersName": "Amaral", "totalValue": 123390.0,
             "expirationDate": None, "negotiationItems": [
                 {"purchaseQuotationItemId": 1, "productId": 7975, "quotedQuantity": 450.0,
                  "negotiatedQuantity": 200.0, "unitPrice": 274.2, "selectedOption": False}]}]},
        {"supplierId": 1900, "negotiations": [
            {"negotiationId": 2, "sellersName": "Casas", "totalValue": 100000.0,
             "expirationDate": "2026-06-15", "negotiationItems": [
                 {"productId": 7975, "negotiatedQuantity": 200.0, "unitPrice": 260.0,
                  "selectedOption": True}]}]},
    ],
}


def test_quotation_decompose():
    rows = t.to_quotation_rows(QUOTATION)
    assert len(rows) == 2  # 2 fornecedores x 1 insumo
    by_sup = {r["supplier_ext"]: r for r in rows}
    assert by_sup["1768"]["resource_code"] == "7975"
    assert by_sup["1768"]["unit_price"] == 274.2
    assert by_sup["1768"]["source_external_id"] == "555:1768:7975"
    assert by_sup["1768"]["valid_until"] == "2026-06-01"  # cai p/ responseDeadline
    assert by_sup["1900"]["valid_until"] == "2026-06-15"  # usa expirationDate
    assert by_sup["1900"]["raw_description"] == "VERGALHAO 10MM"


INVOICE = {"sequentialNumber": 12345, "companyId": 1, "number": "987", "series": "1",
           "issueDate": "2026-06-11", "supplierId": 1768, "billId": 44027,
           "productsAmount": 1000.0, "itemsTotalAmount": 1050.0, "eletronicInvoiceAmount": 1050.0,
           "eletronicInvoiceId": "NFE123", "ipiTax": 50.0, "icmsStTax": 0.0, "consistency": "N"}


def test_invoice():
    r = t.to_invoice(INVOICE)
    assert r["source_external_id"] == "1:12345"
    assert r["total_invoiced"] == 1050.0
    assert r["consistency"] == "N"  # flag de nota inconsistente (F2)
    assert r["supplier_ext"] == "1768"
    assert r["bill_ext"] == "44027"  # vínculo p/ F3 (nota↔pagamento)


def test_budget_item():
    r = t.to_budget_item(BUDGET)
    assert r["source_external_id"] == "202:1"  # chave composta obra:id
    assert r["building_ext"] == "202"
    assert r["resource_code"] == "5001"  # workItemId
    assert r["qty_budgeted"] == 100.0
    assert r["qty_measured"] == 130.0  # base da R4 (medido vs orçado)
    assert r["unit_price_budgeted"] == 90.0
