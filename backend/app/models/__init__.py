"""Modelos ORM. Importar tudo aqui garante que o Alembic enxergue todas as
tabelas e que TENANT_SCOPED seja populado antes das migrações.
"""

from app.models.auth import Membership, Role, User
from app.models.base import TENANT_SCOPED, Base
from app.models.billing import BillingEvent, Plan, Subscription, UsageCounter
from app.models.catalog import CatalogItem, ItemMapping, SinapiReference
from app.models.findings import (
    AuditLog,
    Finding,
    FindingEvidence,
    FindingReview,
    FindingStatus,
    RuleCalibration,
    RuleConfig,
    Severity,
    ValueLedger,
)
from app.models.integrity import Counterparty
from app.models.platform import DeadLetter, EntityHistory, OutboxEvent, RawRecord, TenantSecret
from app.models.sourcing import (
    Bill,
    BudgetItem,
    Creditor,
    Invoice,
    InvoiceItem,
    OrderAuthorization,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseRequest,
    PurchaseRequestItem,
    Quotation,
)
from app.models.tenancy import Company, Project, Tenant

__all__ = [
    "Base",
    "TENANT_SCOPED",
    # tenancy
    "Tenant",
    "Company",
    "Project",
    # auth
    "User",
    "Membership",
    "Role",
    # platform
    "RawRecord",
    "EntityHistory",
    "OutboxEvent",
    "TenantSecret",
    "DeadLetter",
    # sourcing
    "Creditor",
    "BudgetItem",
    "Quotation",
    "PurchaseRequest",
    "PurchaseRequestItem",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "OrderAuthorization",
    "Invoice",
    "InvoiceItem",
    "Bill",
    # catalog
    "CatalogItem",
    "ItemMapping",
    "SinapiReference",
    "Counterparty",
    # findings
    "Finding",
    "FindingEvidence",
    "FindingReview",
    "RuleConfig",
    "RuleCalibration",
    "ValueLedger",
    "AuditLog",
    "FindingStatus",
    "Severity",
    # billing
    "Plan",
    "Subscription",
    "UsageCounter",
    "BillingEvent",
]
