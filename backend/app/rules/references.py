"""Resolvedor de referência de preço (ground-truth.md).

Cascata (ADR-07 grava o snapshot no achado):
  Camada 1 (SINAPI regional)  ->  Camada 0 (mediana histórica do tenant)

Camada 2 (benchmark) entra na Fase 1. Cold-start cai na Camada 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import CatalogItem, SinapiReference
from app.models.sourcing import PurchaseOrderItem


@dataclass
class PriceReference:
    value: Decimal
    layer: str  # "sinapi" | "internal_median"
    snapshot: dict


def _sinapi_reference(session: Session, sinapi_code: str, state: str | None) -> PriceReference | None:
    stmt = select(SinapiReference).where(SinapiReference.sinapi_code == sinapi_code)
    if state:
        stmt = stmt.where(SinapiReference.state == state)
    stmt = stmt.order_by(SinapiReference.period.desc()).limit(1)
    row = session.execute(stmt).scalar_one_or_none()
    if row is None or row.price is None:
        return None
    return PriceReference(
        value=Decimal(str(row.price)),
        layer="sinapi",
        snapshot={
            "layer": "camada_1_sinapi",
            "source": "SINAPI",
            "sinapi_code": sinapi_code,
            "state": row.state,
            "period": row.period,
            "regime": row.regime,
            "value": str(row.price),
        },
    )


def _internal_median(session: Session, catalog_item_id: str) -> PriceReference | None:
    # mediana dos preços unitários já praticados pelo próprio tenant (RLS ativo).
    median = session.execute(
        select(func.percentile_cont(0.5).within_group(PurchaseOrderItem.unit_price)).where(
            PurchaseOrderItem.catalog_item_id == catalog_item_id,
            PurchaseOrderItem.unit_price.is_not(None),
        )
    ).scalar()
    n = session.execute(
        select(func.count()).where(
            PurchaseOrderItem.catalog_item_id == catalog_item_id,
            PurchaseOrderItem.unit_price.is_not(None),
        )
    ).scalar_one()
    if median is None or n < 3:  # cold-start: precisa de massa mínima
        return None
    return PriceReference(
        value=Decimal(str(median)),
        layer="internal_median",
        snapshot={
            "layer": "camada_0_interno",
            "source": "mediana_historica_tenant",
            "n": int(n),
            "value": str(median),
        },
    )


def resolve_price_reference(
    session: Session, catalog_item_id: str, state: str | None
) -> PriceReference | None:
    item = session.get(CatalogItem, catalog_item_id)
    if item is not None and item.sinapi_code:
        ref = _sinapi_reference(session, item.sinapi_code, state)
        if ref is not None:
            return ref
    return _internal_median(session, catalog_item_id)
