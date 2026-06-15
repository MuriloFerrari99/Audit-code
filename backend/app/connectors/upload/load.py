"""Carga de NF-e por upload -> canônico (Invoice + InvoiceItem + retenções).

Tenant-scoped (RLS). XML inválido vira dead_letter (nunca falha em silêncio).
Reaproveita o mesmo canônico/regras da ingestão por conector.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select

from app.connectors.upload.nfe import parse_nfe
from app.connectors.upload.spreadsheet import parse_amount, parse_spreadsheet
from app.core.db import tenant_session
from app.core.logging import get_logger
from app.core.timeutils import to_utc
from app.models.platform import DeadLetter
from app.models.sourcing import Bill, Creditor, Invoice, InvoiceItem, PurchaseOrder

log = get_logger("upload.nfe")


def _dec(v) -> Decimal | None:
    if v in (None, ""):
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def _dt(v):
    if not v:
        return None
    try:
        return to_utc(datetime.fromisoformat(str(v).replace("Z", "+00:00")))
    except ValueError:
        return None


def _date_any(v):
    """Datas de planilha: ISO, dd/mm/aaaa, dd-mm-aaaa ou datetime já tipado."""
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return to_utc(v)
    iso = _dt(v)
    if iso is not None:
        return iso
    s = str(v).strip().replace("-", "/")
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return to_utc(datetime.strptime(s, fmt))
        except ValueError:
            continue
    return None


def _get_or_create_creditor(s, tenant_id: str, cnpj: str | None, nome: str | None):
    if not cnpj:
        return None
    c = s.execute(
        select(Creditor).where(Creditor.source == "upload", Creditor.source_external_id == cnpj)
    ).scalar_one_or_none()
    if c is None:
        c = Creditor(tenant_id=tenant_id, source="upload", source_external_id=cnpj,
                     name=nome or "(fornecedor)", cnpj_cpf=cnpj, content_hash="upload")
        s.add(c)
        s.flush()
    return c


def load_nfe_files(tenant_id: str, files: list[tuple[str, bytes]]) -> dict:
    """files = [(filename, xml_bytes)]. Retorna resumo + dead_letters."""
    summary = {"invoices": 0, "items": 0, "dead_letters": 0}
    with tenant_session(tenant_id) as s:
        for fname, content in files:
            try:
                d = parse_nfe(content)
            except Exception as e:  # XML inválido -> dead-letter visível (A-3)
                s.add(DeadLetter(tenant_id=tenant_id, source="upload", entity_type="invoice",
                                 ref=fname, reason=f"NF-e inválida: {e}"[:500]))
                summary["dead_letters"] += 1
                continue

            chave = d.get("chave") or fname
            creditor = _get_or_create_creditor(s, tenant_id, d.get("emit_cnpj"), d.get("emit_nome"))
            ret = d.get("retencoes") or {}
            inv = s.execute(
                select(Invoice).where(Invoice.source == "upload", Invoice.source_external_id == chave)
            ).scalar_one_or_none()
            if inv is None:
                inv = Invoice(tenant_id=tenant_id, source="upload", source_external_id=chave,
                              content_hash=hashlib.sha256(content).hexdigest())
                s.add(inv)
                summary["invoices"] += 1
            inv.number = d.get("numero")
            inv.series = d.get("serie")
            inv.issued_at = _dt(d.get("emissao"))
            inv.total_invoiced = _dec(d.get("valor_total"))
            inv.products_amount = _dec(d.get("valor_produtos"))
            inv.ipi_tax = _dec(d.get("valor_ipi"))
            inv.nfe_key = chave
            inv.creditor_id = creditor.id if creditor else None
            inv.inss_retention = _dec(ret.get("inss"))
            inv.iss_retention = _dec(ret.get("iss"))
            inv.is_service = bool(ret.get("iss")) or "servic" in (d.get("natureza") or "").lower()
            s.flush()

            # itens (substitui em reupload)
            s.query(InvoiceItem).filter(InvoiceItem.invoice_id == inv.id).delete()
            for it in d.get("itens") or []:
                s.add(InvoiceItem(
                    tenant_id=tenant_id, invoice_id=inv.id,
                    resource_code=it.get("codigo"),
                    raw_description=it.get("descricao") or "(item)",
                    ncm=it.get("ncm"), cfop=it.get("cfop"), unit=it.get("unidade"),
                    qty=_dec(it.get("qtd")), unit_price=_dec(it.get("valor_unit")),
                    total=_dec(it.get("valor_total")),
                ))
                summary["items"] += 1
    log.info("upload.nfe.done", tenant_id=tenant_id, **summary)
    return summary


def _resolve_creditor(s, tenant_id: str, cnpj: str | None, nome: str | None):
    """Resolve por CNPJ; sem CNPJ, cai para o nome (chave estável p/ idempotência)."""
    key = (cnpj or "").strip() or (f"name:{nome.strip()}" if nome else None)
    if not key:
        return None
    c = s.execute(
        select(Creditor).where(Creditor.source == "upload", Creditor.source_external_id == key)
    ).scalar_one_or_none()
    if c is None:
        c = Creditor(tenant_id=tenant_id, source="upload", source_external_id=key,
                     name=(nome or "(fornecedor)").strip(),
                     cnpj_cpf=(cnpj or None), content_hash="upload")
        s.add(c)
        s.flush()
    return c


def load_spreadsheet(tenant_id: str, filename: str, content: bytes) -> dict:
    """Planilha de lançamentos -> Bill (contas a pagar) no canônico.

    Linha sem valor numérico vira dead_letter (visível). source_external_id é
    determinístico por (arquivo, linha, doc, cnpj, valor) -> reupload idempotente,
    mas duas linhas idênticas no MESMO arquivo viram títulos distintos (P1 detecta).
    """
    summary: dict = {"bills": 0, "dead_letters": 0, "mapping": {}}
    parsed = parse_spreadsheet(filename, content)
    summary["mapping"] = parsed["mapping"]
    with tenant_session(tenant_id) as s:
        for row in parsed["rows"]:
            amount = parse_amount(row.get("valor"))
            if amount is None or amount <= 0:
                s.add(DeadLetter(tenant_id=tenant_id, source="upload", entity_type="bill",
                                 ref=f"{filename}:linha {row.get('_row')}",
                                 reason=f"linha sem valor válido: {row.get('valor')!r}"[:500]))
                summary["dead_letters"] += 1
                continue

            doc = (str(row["documento"]).strip() if row.get("documento") else None)
            cnpj = (str(row["cnpj"]).strip() if row.get("cnpj") else None)
            creditor = _resolve_creditor(s, tenant_id, cnpj, row.get("fornecedor"))
            ext = hashlib.sha1(
                f"{filename}|{row['_row']}|{doc}|{cnpj}|{amount}".encode()
            ).hexdigest()

            order_id = None
            pedido = (str(row["pedido"]).strip() if row.get("pedido") else None)
            if pedido:
                po = s.execute(
                    select(PurchaseOrder).where(PurchaseOrder.source_external_id == pedido)
                ).scalars().first()
                order_id = po.id if po else None

            bill = s.execute(
                select(Bill).where(Bill.source == "upload", Bill.source_external_id == ext)
            ).scalar_one_or_none()
            if bill is None:
                bill = Bill(tenant_id=tenant_id, source="upload", source_external_id=ext,
                            content_hash=ext)
                s.add(bill)
                summary["bills"] += 1
            bill.creditor_id = creditor.id if creditor else None
            bill.document_number = doc
            bill.amount = _dec(amount)
            bill.due_date = _date_any(row.get("data"))
            bill.order_id = order_id
    log.info("upload.planilha.done", tenant_id=tenant_id,
             bills=summary["bills"], dead_letters=summary["dead_letters"])
    return summary
