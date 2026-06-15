"""Base do OpenSquad: contexto, resultado e gravação do prontuário."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.agentic import AgentReasoningLog


def new_run_id() -> uuid.UUID:
    """ID que agrupa todos os passos de uma execução do squad."""
    return uuid.uuid4()


@dataclass(slots=True)
class SquadContext:
    """Contexto de uma execução: define país/setor/idioma -> quais adapters ligar."""

    tenant_id: str
    run_id: uuid.UUID = field(default_factory=new_run_id)
    country: str = "BR"
    industry: str = "construction"
    locale: str = "pt-BR"


@dataclass(slots=True)
class AgentResult:
    """Saída de um passo de agente (vira uma linha de AgentReasoningLog)."""

    agent_name: str
    status: str = "ok"  # started|ok|failed|skipped
    confidence: float | None = None
    reasoning: str = ""
    citations: list[str] | None = None
    data: dict | None = None


class SquadAgent:
    """Base comum. Cada papel implementa seu método de execução próprio."""

    name: str = "agent"

    def log(self, session: Session, ctx: SquadContext, result: AgentResult,
            *, document_external_id: str | None = None,
            finding_id: str | None = None) -> AgentReasoningLog:
        """Persiste o passo de raciocínio (tenant-scoped, sob RLS)."""
        row = AgentReasoningLog(
            tenant_id=ctx.tenant_id,
            run_id=ctx.run_id,
            agent_name=result.agent_name,
            status=result.status,
            confidence_score=Decimal(str(result.confidence)) if result.confidence is not None else None,
            reasoning_text=result.reasoning or None,
            legal_citations=result.citations,
            document_external_id=document_external_id,
            finding_id=finding_id,
        )
        session.add(row)
        session.flush()
        return row
