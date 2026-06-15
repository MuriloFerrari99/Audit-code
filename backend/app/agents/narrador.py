"""Agente Narrador (agentes.md): resumo executivo do período.

Números vêm do dado/ledger (o agente NÃO estima R$). Texto em linguagem do dono
é opcional via LLM; sem chave, retorna um resumo templado a partir dos números.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.llm import LLMClient
from app.models.findings import Finding, FindingStatus, ValueLedger


def monthly_summary(
    session: Session, tenant_id: str, period: str, llm: LLMClient | None = None
) -> dict:
    exposed = session.execute(
        select(func.coalesce(func.sum(Finding.exposed_amount), 0)).where(
            Finding.status == FindingStatus.OPEN.value
        )
    ).scalar_one()
    validated = session.execute(
        select(func.coalesce(func.sum(ValueLedger.validated_amount), 0)).where(
            ValueLedger.period == period
        )
    ).scalar_one()
    open_count = session.execute(
        select(func.count()).where(Finding.status == FindingStatus.OPEN.value)
    ).scalar_one()
    by_rule = dict(
        session.execute(select(Finding.rule_id, func.count()).group_by(Finding.rule_id)).all()
    )

    numbers = {
        "period": period,
        "exposed_open": str(Decimal(str(exposed))),
        "validated": str(Decimal(str(validated))),
        "open_findings": int(open_count),
        "by_rule": {k: int(v) for k, v in by_rule.items()},
    }

    text = (
        f"No período {period}, há {numbers['open_findings']} achados em aberto somando "
        f"R$ {numbers['exposed_open']} expostos; R$ {numbers['validated']} já validados."
    )
    if llm is not None:
        prose = llm.complete(
            f"Escreva um resumo executivo curto para o dono da construtora a partir destes "
            f"números (não invente valores): {numbers}",
            tenant_id=tenant_id,
            task="strong",
            max_tokens=600,
        )
        if prose:
            text = prose

    return {"numbers": numbers, "summary": text}
