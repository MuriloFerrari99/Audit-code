"""Modelos ORM. Importar tudo aqui garante que o Alembic enxergue todas as
tabelas e que TENANT_SCOPED seja populado antes das migrações.
"""

from app.models.auth import Membership, Role, User
from app.models.base import TENANT_SCOPED, Base
from app.models.catalog import CatalogItem, ItemMapping
from app.models.findings import (
    AuditLog,
    Finding,
    FindingEvidence,
    FindingReview,
    FindingStatus,
    RuleConfig,
    Severity,
    ValueLedger,
)
from app.models.platform import EntityHistory, OutboxEvent, RawRecord
from app.models.sourcing import (
    Bill,
    BudgetItem,
    Creditor,
    Invoice,
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
    "Bill",
    # catalog
    "CatalogItem",
    "ItemMapping",
    # findings
    "Finding",
    "FindingEvidence",
    "FindingReview",
    "RuleConfig",
    "ValueLedger",
    "AuditLog",
    "FindingStatus",
    "Severity",
]
