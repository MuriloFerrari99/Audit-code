"""Rotas do prontuário agêntico (explicabilidade do OpenSquad)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.service import list_reasoning
from app.api.deps import get_tenant_db

router = APIRouter(prefix="/agents", tags=["agents"])


def _out(r) -> dict:
    return {
        "id": str(r.id),
        "run_id": str(r.run_id),
        "agent_name": r.agent_name,
        "status": r.status,
        "confidence": str(r.confidence_score) if r.confidence_score is not None else None,
        "reasoning": r.reasoning_text,
        "citations": r.legal_citations,
        "document_external_id": r.document_external_id,
        "finding_id": str(r.finding_id) if r.finding_id else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.get("/reasoning")
def reasoning(run_id: str | None = None, limit: int = 100,
              db: Session = Depends(get_tenant_db)) -> dict:
    """Prontuário de raciocínio do squad (filtrável por run_id)."""
    return {"logs": [_out(r) for r in list_reasoning(db, run_id=run_id, limit=limit)]}
