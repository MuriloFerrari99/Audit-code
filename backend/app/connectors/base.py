"""Contrato de conector (T-060, conector-sienge.md §7).

SOMENTE LEITURA. Nenhuma operação de escrita à fonte existe neste contrato.
Adicionar fonte/país = nova implementação desta interface (ver latam-readiness.md).
"""

from __future__ import annotations

import enum
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


class EntityKind(enum.StrEnum):
    CREDITOR = "creditor"
    BUDGET_ITEM = "budget_item"
    QUOTATION = "quotation"
    PURCHASE_REQUEST = "purchase_request"
    PURCHASE_ORDER = "purchase_order"
    INVOICE = "invoice"
    BILL = "bill"


@dataclass
class RawRecord:
    """Registro bruto da fonte, antes de normalizar (vai para raw_record)."""

    entity: EntityKind
    source_external_id: str
    payload: dict[str, Any]


@dataclass
class CanonicalRecord:
    """Registro já mapeado para o modelo canônico."""

    entity: EntityKind
    source_external_id: str
    fields: dict[str, Any]


@dataclass
class ConnectorHealth:
    ok: bool
    detail: str = ""
    checked_at: datetime | None = None


@dataclass
class PullCursor:
    """Watermark/paginação para sync incremental (ADR-10)."""

    since: datetime | None = None
    page: int = 1
    extra: dict[str, Any] = field(default_factory=dict)


class SourceConnector(Protocol):
    source_name: str
    country_code: str

    def authenticate(self) -> None: ...
    def list_entities(self) -> list[EntityKind]: ...
    def pull(self, entity: EntityKind, cursor: PullCursor) -> Iterator[RawRecord]: ...
    def normalize(self, raw: RawRecord) -> CanonicalRecord: ...
    def health(self) -> ConnectorHealth: ...
