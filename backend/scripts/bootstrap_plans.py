"""Bootstrap do catálogo de planos (Fase 2). Global, sem RLS -> admin_session.

Idempotente (upsert por `code`). O plano "corporativo" (>2000 notas) tem
invoice_limit=3000 e overage_price=1.90, conforme definido pelo founder.
Base_price fica a definir comercialmente (gtm.md §9).

Uso: python -m scripts.bootstrap_plans
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.db import admin_session
from app.core.logging import get_logger
from app.models.billing import Plan

log = get_logger("bootstrap.plans")

PLANS = [
    {
        "code": "essencial",
        "name": "Essencial (até 2000 notas)",
        "base_price": Decimal("0"),     # a definir comercialmente
        "invoice_limit": 2000,
        "overage_price": Decimal("2.50"),
        "gainshare_pct": None,
        "active": True,
    },
    {
        "code": "corporativo",
        "name": "Corporativo (2000+ notas)",
        "base_price": Decimal("0"),     # a definir comercialmente
        "invoice_limit": 3000,
        "overage_price": Decimal("1.90"),
        "gainshare_pct": None,
        "active": True,
    },
]


def bootstrap_plans() -> None:
    with admin_session() as s:
        for p in PLANS:
            stmt = pg_insert(Plan).values(**p).on_conflict_do_update(
                index_elements=["code"],
                set_={
                    "name": p["name"],
                    "base_price": p["base_price"],
                    "invoice_limit": p["invoice_limit"],
                    "overage_price": p["overage_price"],
                    "gainshare_pct": p["gainshare_pct"],
                    "active": p["active"],
                },
            )
            s.execute(stmt)
    log.info("bootstrap.plans.done", n=len(PLANS))


if __name__ == "__main__":
    bootstrap_plans()
    print(f"{len(PLANS)} planos criados/atualizados (essencial, corporativo).")
