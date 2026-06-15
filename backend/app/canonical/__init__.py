"""Modelo Canônico de Dados (CDM) — a interface universal do domínio.

Nenhum documento (NF-e BR, NFS-e, planilha, PDF US, EDI) entra no banco ou nos
agentes na sua forma nativa: um Adapter (porta de entrada) o mapeia para
`CanonicalDocument`/`CanonicalItem`. O Core e o OpenSquad só conhecem o CDM —
é isso que torna o motor agnóstico a país e setor (arquitetura hexagonal).
"""

from app.canonical.document import (
    CanonicalDocument,
    CanonicalItem,
    CanonicalParty,
    CanonicalRetentions,
    DocumentType,
    SourceFormat,
)

__all__ = [
    "CanonicalDocument",
    "CanonicalItem",
    "CanonicalParty",
    "CanonicalRetentions",
    "DocumentType",
    "SourceFormat",
]
