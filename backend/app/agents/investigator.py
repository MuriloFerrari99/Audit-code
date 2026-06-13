"""Agente Investigador (agentes.md): monta o dossiê de evidência da cadeia.

Núcleo determinístico (puxa a cadeia do canônico, read-only). Narrativa em
linguagem natural é opcional via LLM; sem chave, retorna o dossiê estruturado.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient
from app.models.findings import Finding, FindingEvidence
from app.models.sourcing import Bill, PurchaseOrder, PurchaseOrderItem, Quotation


def build_dossier(session: Session, finding_id: str, llm: LLMClient | None = None) -> dict:
    finding = session.get(Finding, finding_id)
    if finding is None:
        return {"error": "achado não encontrado"}

    evidence = list(
        session.execute(
            select(FindingEvidence).where(FindingEvidence.finding_id == finding_id)
        ).scalars()
    )

    dossier = {
        "finding": {
            "id": str(finding.id),
            "rule_id": finding.rule_id,
            "severity": finding.severity,
            "status": finding.status,
            "exposed_amount": str(finding.exposed_amount) if finding.exposed_amount else None,
            "title": finding.title,
            "reference": finding.reference_snapshot,
            "config": finding.config_snapshot,
        },
        "evidence": [
            {"entity_type": e.entity_type, "role": e.role, "snippet": e.snippet, "value": e.value}
            for e in evidence
        ],
        "chain": _build_chain(session, evidence),
    }

    if llm is not None:
        narrative = llm.complete(
            _dossier_prompt(dossier),
            tenant_id=str(finding.tenant_id),
            task="strong",
            max_tokens=800,
        )
        if narrative:
            dossier["narrative"] = narrative
    return dossier


def _build_chain(session: Session, evidence: list[FindingEvidence]) -> dict:
    chain: dict = {}
    for e in evidence:
        if e.entity_type == "purchase_order" and e.entity_id:
            order = session.get(PurchaseOrder, e.entity_id)
            if order:
                chain["order"] = {"id": str(order.id), "total": str(order.total),
                                  "ordered_at": str(order.ordered_at)}
                items = session.execute(
                    select(PurchaseOrderItem).where(PurchaseOrderItem.order_id == order.id)
                ).scalars()
                chain["order_items"] = [
                    {"desc": i.raw_description, "qty": str(i.qty), "unit_price": str(i.unit_price)}
                    for i in items
                ]
        if e.entity_type == "quotation" and e.entity_id:
            q = session.get(Quotation, e.entity_id)
            if q:
                chain["cheapest_quotation"] = {"unit_price": str(q.unit_price),
                                               "valid_until": str(q.valid_until)}
        if e.entity_type == "bill" and e.entity_id:
            b = session.get(Bill, e.entity_id)
            if b:
                chain["payment"] = {"amount": str(b.amount), "paid_at": str(b.paid_at)}
    return chain


def _dossier_prompt(dossier: dict) -> str:
    return (
        "Resuma este achado de auditoria para um controller, citando a evidência e o "
        "valor em R$. Seja factual; é advisory, não veredito.\n\n"
        f"{dossier}"
    )
