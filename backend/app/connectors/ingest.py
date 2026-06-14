"""Ingestão read-only: fonte -> raw_record (+outbox) (T-064, ADR-06/01).

Idempotente por (tenant, source, entity, source_external_id) + content_hash.
A transformação raw -> canônico é um passo separado que depende do mapeamento
campo a campo final (normalize), fixado contra a resposta real do Sienge.
"""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select

from app.connectors.base import EntityKind, PullCursor, SourceConnector
from app.core.db import tenant_session
from app.core.logging import get_logger
from app.models.platform import RawRecord

log = get_logger("connector.ingest")


def _hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def ingest_raw(connector: SourceConnector, tenant_id: str,
               entities: list[EntityKind] | None = None) -> dict[str, int]:
    """Puxa cada entidade e grava em raw_record (upsert por hash). Retorna
    {entidade: novos/atualizados}."""
    connector.authenticate()
    summary: dict[str, int] = {}
    for entity in entities or connector.list_entities():
        changed = 0
        with tenant_session(tenant_id) as s:
            for raw in connector.pull(entity, PullCursor()):
                h = _hash(raw.payload)
                existing = s.execute(
                    select(RawRecord).where(
                        RawRecord.source == connector.source_name,
                        RawRecord.entity_type == entity.value,
                        RawRecord.source_external_id == raw.source_external_id,
                    )
                ).scalar_one_or_none()
                if existing is None:
                    s.add(RawRecord(
                        tenant_id=tenant_id, source=connector.source_name,
                        entity_type=entity.value, source_external_id=raw.source_external_id,
                        payload=raw.payload, content_hash=h,
                    ))
                    changed += 1
                elif existing.content_hash != h:
                    existing.payload = raw.payload
                    existing.content_hash = h
                    changed += 1
        summary[entity.value] = changed
        log.info("ingest.entity", entity=entity.value, changed=changed)
    return summary
