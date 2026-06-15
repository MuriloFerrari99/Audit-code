"""Leitura do prontuário agêntico (AgentReasoningLog), tenant-scoped."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agentic import AgentReasoningLog


def list_reasoning(session: Session, *, run_id: str | None = None,
                   limit: int = 100) -> list[AgentReasoningLog]:
    stmt = select(AgentReasoningLog).order_by(AgentReasoningLog.created_at.desc())
    if run_id:
        stmt = stmt.where(AgentReasoningLog.run_id == run_id)
    return list(session.execute(stmt.limit(limit)).scalars())
