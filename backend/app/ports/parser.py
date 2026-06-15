"""Port de entrada: transforma bytes brutos em CDM."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.canonical.document import CanonicalDocument


@runtime_checkable
class DocumentParser(Protocol):
    """Adapter de ingestão (NF-e, NFS-e, planilha, PDF US, EDI...)."""

    source_format: str

    def can_parse(self, filename: str, content: bytes) -> bool:
        """True se este adapter reconhece o arquivo."""
        ...

    def parse(self, filename: str, content: bytes) -> list[CanonicalDocument]:
        """Bytes -> 1+ documentos canônicos. Lança ValueError se inválido."""
        ...
