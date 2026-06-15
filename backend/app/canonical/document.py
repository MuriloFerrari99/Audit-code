"""Estruturas do Modelo Canônico de Dados (CDM).

Imutável e independente de framework (puro Python/Decimal) — pode ser serializado,
versionado e auditado. Adapters de entrada produzem isto; o Core consome.
"""

from __future__ import annotations

import enum
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal


class DocumentType(enum.StrEnum):
    """Natureza do documento, independente do país/formato."""

    GOODS_INVOICE = "goods_invoice"      # nota de mercadoria (NF-e BR, US invoice)
    SERVICE_INVOICE = "service_invoice"  # nota de serviço (NFS-e BR)
    BILL = "bill"                        # título / contas a pagar (planilha, EDI)
    PURCHASE_ORDER = "purchase_order"    # pedido de compra
    OTHER = "other"


class SourceFormat(enum.StrEnum):
    """Formato bruto de origem — define qual Adapter o produziu."""

    NFE = "nfe"                # XML SEFAZ (BR mercadoria)
    NFSE = "nfse"              # XML ABRASF/municipal (BR serviço)
    SPREADSHEET = "spreadsheet"  # CSV/XLSX
    US_PDF_INVOICE = "us_pdf_invoice"  # futuro (EUA)
    EDI = "edi"                # futuro
    ERP_API = "erp_api"        # conector de ERP (Sienge/TOTVS/QuickBooks)


@dataclass(frozen=True, slots=True)
class CanonicalParty:
    """Emitente ou destinatário, agnóstico a país (tax_id = CNPJ/EIN/...)."""

    name: str | None = None
    tax_id: str | None = None       # CNPJ (BR), EIN (US), etc.
    country: str = "BR"             # ISO-3166 alpha-2


@dataclass(frozen=True, slots=True)
class CanonicalRetentions:
    """Retenções/impostos retidos (genérico; campos não usados ficam None)."""

    inss: Decimal | None = None
    iss: Decimal | None = None
    pis: Decimal | None = None
    cofins: Decimal | None = None
    csll: Decimal | None = None
    irrf: Decimal | None = None


@dataclass(frozen=True, slots=True)
class CanonicalItem:
    """Linha de item — base da auditoria de preço/contrato."""

    description: str
    code: str | None = None          # código do insumo/serviço (resource_code, SKU)
    classification: str | None = None  # NCM/CFOP (BR), HS code, etc.
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    total: Decimal | None = None


@dataclass(frozen=True, slots=True)
class CanonicalDocument:
    """Documento financeiro universal. Saída de TODO Adapter de entrada."""

    source_format: SourceFormat
    document_type: DocumentType
    external_id: str                 # chave de origem (chave NF-e, hash da linha...)
    country: str = "BR"
    currency: str = "BRL"
    number: str | None = None
    series: str | None = None
    issued_at: datetime | None = None
    issuer: CanonicalParty | None = None
    recipient: CanonicalParty | None = None
    total_amount: Decimal | None = None
    items: list[CanonicalItem] = field(default_factory=list)
    retentions: CanonicalRetentions | None = None
    is_service: bool = False
    # rastreabilidade: referência ao documento bruto (sem PII expandida aqui)
    raw_ref: str | None = None

    def to_dict(self) -> dict:
        """Serialização estável (Decimal -> str) p/ log/auditoria."""

        def _enc(v):
            if isinstance(v, Decimal):
                return str(v)
            if isinstance(v, datetime):
                return v.isoformat()
            if isinstance(v, enum.Enum):
                return v.value
            return v

        def _walk(o):
            if isinstance(o, dict):
                return {k: _walk(_enc(v)) for k, v in o.items()}
            if isinstance(o, list):
                return [_walk(_enc(v)) for v in o]
            return _enc(o)

        return _walk(asdict(self))
