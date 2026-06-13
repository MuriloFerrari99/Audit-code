"""Camada de ingestão. Conectores read-only por fonte (Sienge primeiro)."""

from app.connectors.base import (
    CanonicalRecord,
    ConnectorHealth,
    EntityKind,
    RawRecord,
    SourceConnector,
)

__all__ = [
    "SourceConnector",
    "RawRecord",
    "CanonicalRecord",
    "EntityKind",
    "ConnectorHealth",
]
