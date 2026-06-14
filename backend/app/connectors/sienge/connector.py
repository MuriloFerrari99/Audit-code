"""Conector Sienge (T-063..T-066) — SOMENTE LEITURA.

Auth Basic por subdomínio, via SecretProvider (ADR-11). Validado contra a API
real da Alumbra (ver docs/conector-sienge.md §8b). Sem credencial, cai em modo
fixtures (ADR-13).

Comportamentos reais tratados aqui:
- `bills` e bulk `purchase-quotations` exigem janela de data (startDate/endDate).
- bulk-data fica em `/public/api/bulk-data/v1`.
- itens do pedido são sub-recurso: `/purchase-orders/{id}/items`.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from app.connectors.base import (
    CanonicalRecord,
    ConnectorHealth,
    EntityKind,
    PullCursor,
    RawRecord,
)
from app.connectors.http import ResilientClient, TokenBucket
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.secrets import SecretProvider
from app.core.timeutils import now_utc, to_utc

log = get_logger("connector.sienge")

FIXTURES = Path(__file__).parent / "fixtures"
HOST = "https://api.sienge.com.br"
BACKFILL_DAYS = 730  # janela default de carga inicial


@dataclass
class EndpointSpec:
    path: str  # relativo após a base de versão
    bulk: bool = False
    needs_date: bool = False
    list_key: str = "results"


# Apenas os endpoints validados na API real. purchase_request (sem GET de
# coleção) e budget/orçamento (recurso a definir) ficam fora do MVP — ver §8b.
ENDPOINTS: dict[EntityKind, EndpointSpec] = {
    EntityKind.CREDITOR: EndpointSpec("/creditors"),
    EntityKind.PURCHASE_ORDER: EndpointSpec("/purchase-orders"),
    EntityKind.BILL: EndpointSpec("/bills", needs_date=True),
    EntityKind.QUOTATION: EndpointSpec("/purchase-quotations", bulk=True, needs_date=True, list_key="data"),
    EntityKind.BUDGET_ITEM: EndpointSpec("/building-cost-estimation-items", bulk=True, list_key="data"),
    EntityKind.INVOICE: EndpointSpec("/purchase-invoices"),
}


class SiengeConnector:
    source_name = "sienge"
    country_code = "BR"

    def __init__(self, tenant_id: str, secrets: SecretProvider, use_fixtures: bool | None = None):
        self.tenant_id = tenant_id
        self._secrets = secrets
        self._client: ResilientClient | None = None
        self._sub: str | None = None
        self._use_fixtures = use_fixtures if use_fixtures is not None else not self._has_creds()

    def _has_creds(self) -> bool:
        return self._secrets.get_optional(f"tenant/{self.tenant_id}/sienge/subdomain") is not None

    def authenticate(self) -> None:
        if self._use_fixtures:
            return
        self._sub = self._secrets.get(f"tenant/{self.tenant_id}/sienge/subdomain")
        user = self._secrets.get(f"tenant/{self.tenant_id}/sienge/user")
        pwd = self._secrets.get(f"tenant/{self.tenant_id}/sienge/password")
        bucket = TokenBucket(get_settings().redis_url, rate_per_sec=2.5, burst=5)
        self._client = ResilientClient(HOST, (user, pwd), bucket, tenant_key=self.tenant_id)

    def _base(self, spec: EndpointSpec) -> str:
        ver = "bulk-data/v1" if spec.bulk else "v1"
        return f"/{self._sub}/public/api/{ver}{spec.path}"

    def list_entities(self) -> list[EntityKind]:
        return list(ENDPOINTS.keys())

    def pull(self, entity: EntityKind, cursor: PullCursor) -> Iterator[RawRecord]:
        if self._use_fixtures:
            yield from self._pull_fixtures(entity)
            return
        yield from self._pull_live(entity, cursor)

    def _pull_fixtures(self, entity: EntityKind) -> Iterator[RawRecord]:
        path = FIXTURES / f"{entity.value}.json"
        if not path.exists():
            return
        for row in json.loads(path.read_text()):
            yield RawRecord(entity=entity, source_external_id=str(row.get("id")), payload=row)

    def _date_window(self, cursor: PullCursor) -> dict:
        end = now_utc()
        start = cursor.since or (end - timedelta(days=BACKFILL_DAYS))
        return {"startDate": start.strftime("%Y-%m-%d"), "endDate": end.strftime("%Y-%m-%d")}

    def _pull_live(self, entity: EntityKind, cursor: PullCursor) -> Iterator[RawRecord]:
        assert self._client is not None, "chame authenticate() antes do pull"
        spec = ENDPOINTS[entity]
        params: dict = {}
        if spec.needs_date:
            params.update(self._date_window(cursor))

        def emit(rows):
            for row in rows:
                ext = str(row.get("id") or row.get("purchaseQuotationId")
                          or row.get("sequentialNumber") or row.get("documentNumber"))
                yield RawRecord(entity=entity, source_external_id=ext, payload=row)

        if spec.bulk:
            # bulk-data retorna o conjunto completo em uma chamada (sem offset).
            resp = self._client.get(self._base(spec), params=params)
            data = resp.json()
            rows = data.get(spec.list_key, []) if isinstance(data, dict) else data
            yield from emit(rows or [])
            return

        # REST: paginação por offset até esgotar.
        limit = 200
        offset = (cursor.page - 1) * limit
        while True:
            resp = self._client.get(self._base(spec), params={**params, "limit": limit, "offset": offset})
            data = resp.json()
            rows = data.get(spec.list_key, []) if isinstance(data, dict) else data
            if not rows:
                break
            yield from emit(rows)
            if len(rows) < limit:
                break
            offset += limit

    def pull_order_items(self, order_id: str) -> list[dict]:
        """Sub-recurso de itens do pedido (não vem na listagem)."""
        assert self._client is not None
        resp = self._client.get(f"/{self._sub}/public/api/v1/purchase-orders/{order_id}/items")
        data = resp.json()
        return data.get("results", []) if isinstance(data, dict) else data

    def normalize(self, raw: RawRecord) -> CanonicalRecord:
        """Mapa campo a campo — campos reais validados (§8b)."""
        p = raw.payload
        base = {
            "tenant_id": self.tenant_id,
            "source": "sienge",
            "source_external_id": raw.source_external_id,
            "source_payload": p,
        }
        if raw.entity == EntityKind.PURCHASE_ORDER:
            base.update(
                total=p.get("totalAmount"),
                status=p.get("status"),
                ordered_at=_dt(p.get("date") or p.get("createdAt")),
                # supplierId/buildingId resolvidos para creditor_id/project_id na carga canônica
            )
        elif raw.entity == EntityKind.BILL:
            base.update(
                amount=p.get("totalInvoiceAmount"),
                status=p.get("status"),
                due_date=_dt(p.get("dueDate")),
                paid_at=None,  # pagamento por parcela (sub-recurso de installments) — Fase 1
            )
        elif raw.entity == EntityKind.CREDITOR:
            base.update(name=p.get("name"), cnpj_cpf=p.get("cnpj") or p.get("cpf"))
        # QUOTATION: itens/fornecedores aninhados (purchaseQuotationItems/Suppliers) —
        # decompostos na carga canônica (Fase de ingest canônica).
        return CanonicalRecord(entity=raw.entity, source_external_id=raw.source_external_id, fields=base)

    def health(self) -> ConnectorHealth:
        if self._use_fixtures:
            return ConnectorHealth(ok=True, detail="modo fixtures (sem credencial)", checked_at=now_utc())
        try:
            self.authenticate()
            assert self._client is not None
            self._client.get(self._base(ENDPOINTS[EntityKind.CREDITOR]), params={"limit": 1})
            return ConnectorHealth(ok=True, detail="ok", checked_at=now_utc())
        except Exception as e:  # pragma: no cover
            return ConnectorHealth(ok=False, detail=str(e), checked_at=now_utc())


def _dt(value):
    if not value:
        return None
    try:
        return to_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except ValueError:
        return None
