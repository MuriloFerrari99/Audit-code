"""Seed sintético (T-170) — dados no formato canônico que disparam as 6 regras.

Não depende de credencial Sienge nem do PoC: gera um cenário determinístico para
desenvolver e testar o motor ponta a ponta. Quando o dataset sintético do PoC
(schema Sienge) chegar, substituímos por ele.

Uso: python -m scripts.seed_synthetic
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import text

from app.core.db import admin_session, tenant_session
from app.core.security import hash_password
from app.models.auth import Membership, Role, User
from app.models.catalog import CatalogItem, SinapiReference
from app.models.sourcing import (
    Bill,
    BudgetItem,
    Creditor,
    Invoice,
    OrderAuthorization,
    PurchaseOrder,
    PurchaseOrderItem,
    Quotation,
)
from app.models.tenancy import Company, Project

TENANT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
SEED_EMAIL = "founder@cliente.com"
SEED_PASSWORD = "audit12345"

D = Decimal

# Tabelas tenant-scoped a limpar no reset (ordem segura via CASCADE não necessária
# pois deletamos todas do tenant).
_TENANT_TABLES = [
    "finding_evidence", "finding_review", "value_ledger", "finding",
    "order_authorization", "purchase_order_item", "purchase_request_item",
    "invoice", "bill", "quotation", "budget_item", "purchase_order",
    "purchase_request", "creditor", "item_mapping", "project", "company",
    "raw_record", "entity_history", "outbox_event",
]


def reset() -> None:
    """Remove dados de um seed anterior — torna o seed/teste repetível."""
    with tenant_session(str(TENANT_ID)) as s:
        for table in _TENANT_TABLES:
            s.execute(text(f"DELETE FROM {table}"))  # RLS limita ao tenant atual
    with admin_session() as s:
        s.execute(text("DELETE FROM audit_log WHERE tenant_id = :t"), {"t": TENANT_ID})
        s.execute(text("DELETE FROM sinapi_reference WHERE sinapi_code IN ('1234','5678')"))
        s.execute(text("DELETE FROM catalog_item WHERE canonical_name IN "
                       "('Cimento CP-II 50kg','Aço CA-50 10mm','Brita 1')"))


def _dt(days_ago: int) -> datetime:
    return datetime(2026, 6, 1, tzinfo=timezone.utc) - timedelta(days=days_ago)


def _sourced(**kw):
    kw.setdefault("source", "seed")
    kw.setdefault("content_hash", "seed")
    return kw


def seed() -> dict:
    reset()
    cimento = uuid.uuid4()
    aco = uuid.uuid4()
    brita = uuid.uuid4()

    # Referência pública e catálogo (sem RLS).
    with admin_session() as s:
        # Tenant (tabela sem RLS)
        s.execute(
            text("INSERT INTO tenant (id, name) VALUES (:id, :n) ON CONFLICT (id) DO NOTHING"),
            {"id": TENANT_ID, "n": "Construtora Zero"},
        )
        # Catálogo
        s.add_all(
            [
                CatalogItem(id=cimento, canonical_name="Cimento CP-II 50kg", sinapi_code="1234",
                            unit="sc"),
                CatalogItem(id=aco, canonical_name="Aço CA-50 10mm", sinapi_code=None, unit="kg"),
                CatalogItem(id=brita, canonical_name="Brita 1", sinapi_code="5678", unit="m3"),
            ]
        )
        # SINAPI: cimento ref 30/sc; brita ref 90/m3
        s.add_all(
            [
                SinapiReference(sinapi_code="1234", state="PR", period="2026-05", unit="sc", price=D("30")),
                SinapiReference(sinapi_code="5678", state="PR", period="2026-05", unit="m3", price=D("90")),
            ]
        )
        # Usuário + membership (owner)
        existing = s.execute(
            text("SELECT id FROM app_user WHERE email = :e"),
            {"e": SEED_EMAIL},
        ).first()
        if not existing:
            uid = uuid.uuid4()
            s.add(User(id=uid, email=SEED_EMAIL, password_hash=hash_password(SEED_PASSWORD),
                       full_name="Founder"))
            s.add(Membership(user_id=uid, tenant_id=TENANT_ID, role=Role.OWNER.value))

    # Dados de cliente (com RLS).
    with tenant_session(str(TENANT_ID)) as s:
        company_id = uuid.uuid4()
        project_id = uuid.uuid4()
        s.add(Company(id=company_id, tenant_id=TENANT_ID, name="Empresa Zero",
                      cnpj="00.000.000/0001-00", state="PR"))
        s.add(Project(id=project_id, tenant_id=TENANT_ID, company_id=company_id,
                      name="Obra Centro", state="PR", external_code="OBRA-001"))

        forn_a = uuid.uuid4()
        forn_b = uuid.uuid4()
        s.add_all([
            Creditor(**_sourced(tenant_id=TENANT_ID, source_external_id="F-A", name="Fornecedor A",
                                id=forn_a)),
            Creditor(**_sourced(tenant_id=TENANT_ID, source_external_id="F-B", name="Fornecedor B",
                                id=forn_b)),
        ])

        # --- R1: sobrepreço de cimento (40 vs ref 30) ---
        o1 = uuid.uuid4()
        s.add(PurchaseOrder(**_sourced(tenant_id=TENANT_ID, source_external_id="PO-1", id=o1,
                                       project_id=project_id, creditor_id=forn_a,
                                       total=D("4000"), ordered_at=_dt(20))))
        s.add(PurchaseOrderItem(tenant_id=TENANT_ID, order_id=o1, catalog_item_id=cimento,
                                raw_description="Cimento CP-II", qty=D("100"),
                                unit_price=D("40"), total=D("4000")))

        # --- R2: cotação perdida de aço (pedido 50, cotação válida 42) ---
        o2 = uuid.uuid4()
        s.add(PurchaseOrder(**_sourced(tenant_id=TENANT_ID, source_external_id="PO-2", id=o2,
                                       project_id=project_id, creditor_id=forn_a,
                                       total=D("5000"), ordered_at=_dt(15))))
        s.add(PurchaseOrderItem(tenant_id=TENANT_ID, order_id=o2, catalog_item_id=aco,
                                raw_description="Aço CA-50 10mm", qty=D("100"),
                                unit_price=D("50"), total=D("5000")))
        s.add(Quotation(**_sourced(tenant_id=TENANT_ID, source_external_id="Q-1",
                                   creditor_id=forn_b, catalog_item_id=aco,
                                   raw_description="Vergalhão 10.0", qty=D("100"),
                                   unit_price=D("42"), valid_until=_dt(0))))

        # --- R3: fracionamento (3 pedidos 48000, alçada 50000, janela 30d) ---
        for i in range(3):
            oid = uuid.uuid4()
            s.add(PurchaseOrder(**_sourced(tenant_id=TENANT_ID, source_external_id=f"PO-FR-{i}",
                                           id=oid, project_id=project_id, creditor_id=forn_b,
                                           total=D("48000"), ordered_at=_dt(25 - i * 5))))

        # --- R4: estouro de quantidade (brita orçada 100, pedida 130) ---
        s.add(BudgetItem(**_sourced(tenant_id=TENANT_ID, source_external_id="BUD-1",
                                    project_id=project_id, catalog_item_id=brita,
                                    raw_description="Brita 1", unit="m3", qty_budgeted=D("100"),
                                    unit_price_budgeted=D("90"), total_budgeted=D("9000"))))
        o4 = uuid.uuid4()
        s.add(PurchaseOrder(**_sourced(tenant_id=TENANT_ID, source_external_id="PO-4", id=o4,
                                       project_id=project_id, creditor_id=forn_a,
                                       total=D("11700"), ordered_at=_dt(10))))
        s.add(PurchaseOrderItem(tenant_id=TENANT_ID, order_id=o4, catalog_item_id=brita,
                                raw_description="Brita 1", qty=D("130"),
                                unit_price=D("90"), total=D("11700")))

        # --- R5: divergência pedido->pagamento (pedido 10000, pago 11000) ---
        o5 = uuid.uuid4()
        s.add(PurchaseOrder(**_sourced(tenant_id=TENANT_ID, source_external_id="PO-5", id=o5,
                                       project_id=project_id, creditor_id=forn_a,
                                       total=D("10000"), ordered_at=_dt(12))))
        s.add(Bill(**_sourced(tenant_id=TENANT_ID, source_external_id="BILL-1", order_id=o5,
                              creditor_id=forn_a, amount=D("11000"), status="paid",
                              paid_at=_dt(5))))

        # --- R6: sem concorrência (pedido 80000 > 50000, item sem cotação concorrente) ---
        o6 = uuid.uuid4()
        s.add(PurchaseOrder(**_sourced(tenant_id=TENANT_ID, source_external_id="PO-6", id=o6,
                                       project_id=project_id, creditor_id=forn_a,
                                       total=D("80000"), ordered_at=_dt(8))))
        s.add(PurchaseOrderItem(tenant_id=TENANT_ID, order_id=o6, catalog_item_id=brita,
                                raw_description="Brita 1 - grande volume", qty=D("800"),
                                unit_price=D("100"), total=D("80000")))
        # autorização (alçada vigente, p/ contexto de R3/R6)
        s.add(OrderAuthorization(tenant_id=TENANT_ID, order_id=o6, level="diretoria",
                                 authorized_by="diretor", authorized_at=_dt(8),
                                 threshold_at_time=D("50000")))

        # nota de atendimento (para futura dimensão fiscal / R4 com qty atendida)
        s.add(Invoice(**_sourced(tenant_id=TENANT_ID, source_external_id="INV-1", order_id=o4,
                                 creditor_id=forn_a, number="123", qty_delivered=D("130"),
                                 unit_price_invoiced=D("90"), total_invoiced=D("11700"),
                                 issued_at=_dt(6))))

    return {"tenant_id": str(TENANT_ID), "email": SEED_EMAIL, "password": SEED_PASSWORD}


if __name__ == "__main__":
    info = seed()
    print("seed concluído:", info)
