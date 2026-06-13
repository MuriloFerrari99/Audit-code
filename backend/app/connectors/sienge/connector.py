"""Conector Sienge (T-063..T-066) — SOMENTE LEITURA.

Auth Basic por subdomínio, via SecretProvider (ADR-11). O pull ao vivo precisa
das credenciais reais (Q1/Q7); até lá, em modo dev/teste, lê de fixtures
sanitizadas (ADR-13) para exercitar paginação/normalização sem credencial.

O mapa de endpoints segue docs/conector-sienge.md §3. O mapeamento campo a campo
(normalize) é o esqueleto a ser fixado contra a resposta real no onboarding.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
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

# Mapa entidade -> endpoint (conector-sienge.md §3). REST/Bulk indicado.
ENDPOINTS: dict[EntityKind, str] = {
    EntityKind.CREDITOR: "/creditors",
    EntityKind.BUDGET_ITEM: "/building-cost-estimations",
    EntityKind.QUOTATION: "/bulk-data/v1/purchase-quotations",
    EntityKind.PURCHASE_REQUEST: "/purchase-requests",
    EntityKind.PURCHASE_ORDER: "/purchase-orders",
    EntityKind.INVOICE: "/purchase-invoices/deliveries-attended",
    EntityKind.BILL: "/bills",
}


class SiengeConnector:
    source_name = "sienge"
    country_code = "BR"

    def __init__(self, tenant_id: str, secrets: SecretProvider, use_fixtures: bool | None = None):
        self.tenant_id = tenant_id
        self._secrets = secrets
        self._client: ResilientClient | None = None
        # Sem credencial -> modo fixtures (dev/teste).
        self._use_fixtures = use_fixtures if use_fixtures is not None else not self._has_creds()

    # --- credenciais -------------------------------------------------------
    def _has_creds(self) -> bool:
        return self._secrets.get_optional(f"tenant/{self.tenant_id}/sienge/subdomain") is not None

    def authenticate(self) -> None:
        if self._use_fixtures:
            return
        sub = self._secrets.get(f"tenant/{self.tenant_id}/sienge/subdomain")
        user = self._secrets.get(f"tenant/{self.tenant_id}/sienge/user")
        pwd = self._secrets.get(f"tenant/{self.tenant_id}/sienge/password")
        base = f"https://api.sienge.com.br/{sub}/public/api/v1"
        bucket = TokenBucket(get_settings().redis_url, rate_per_sec=5.0, burst=10)
        self._client = ResilientClient(base, (user, pwd), bucket, tenant_key=self.tenant_id)

    # --- contrato ----------------------------------------------------------
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

    def _pull_live(self, entity: EntityKind, cursor: PullCursor) -> Iterator[RawRecord]:
        assert self._client is not None, "chame authenticate() antes do pull"
        path = ENDPOINTS[entity]
        params: dict = {"limit": 200, "offset": (cursor.page - 1) * 200}
        if cursor.since:
            params["modifiedAfter"] = cursor.since.isoformat()  # TODO(Q1): nome real do filtro
        resp = self._client.get(path, params=params)
        data = resp.json()
        rows = data.get("results", data) if isinstance(data, dict) else data
        for row in rows:
            yield RawRecord(entity=entity, source_external_id=str(row.get("id")), payload=row)

    def normalize(self, raw: RawRecord) -> CanonicalRecord:
        """Mapa campo a campo (esqueleto — fixar contra a API real, Q1).

        Estrutura estável; nomes de campo do Sienge confirmados no onboarding.
        """
        p = raw.payload
        base = {
            "tenant_id": self.tenant_id,
            "source": "sienge",
            "source_external_id": raw.source_external_id,
            "source_payload": p,
        }
        if raw.entity == EntityKind.PURCHASE_ORDER:
            base.update(
                total=p.get("totalValue") or p.get("total"),
                status=p.get("status"),
                ordered_at=_dt(p.get("date") or p.get("orderedAt")),
                # creditor_id/project_id resolvidos por FK na carga (TODO Q1)
            )
        elif raw.entity == EntityKind.BILL:
            base.update(
                amount=p.get("amount") or p.get("value"),
                status=p.get("status"),
                due_date=_dt(p.get("dueDate")),
                paid_at=_dt(p.get("paymentDate")),
            )
        elif raw.entity == EntityKind.CREDITOR:
            base.update(name=p.get("name"), cnpj_cpf=p.get("cnpj") or p.get("document"))
        # demais entidades: mapeadas no onboarding (mesmo padrão).
        return CanonicalRecord(entity=raw.entity, source_external_id=raw.source_external_id, fields=base)

    def health(self) -> ConnectorHealth:
        if self._use_fixtures:
            return ConnectorHealth(ok=True, detail="modo fixtures (sem credencial)", checked_at=now_utc())
        try:
            self.authenticate()
            assert self._client is not None
            self._client.get(ENDPOINTS[EntityKind.CREDITOR], params={"limit": 1})
            return ConnectorHealth(ok=True, detail="ok", checked_at=now_utc())
        except Exception as e:  # pragma: no cover
            return ConnectorHealth(ok=False, detail=str(e), checked_at=now_utc())


def _dt(value):
    from datetime import datetime

    if not value:
        return None
    try:
        return to_utc(datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except ValueError:
        return None
