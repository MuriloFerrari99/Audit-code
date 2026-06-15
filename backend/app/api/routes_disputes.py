"""Rotas de disputas/mitigação (Agente Executor). Ação restrita por papel."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_tenant_db, require_role
from app.disputes.service import list_disputes, mitigate_finding
from app.models.auth import Role

router = APIRouter(prefix="/disputes", tags=["disputes"])


def _out(d) -> dict:
    return {
        "id": str(d.id), "finding_id": str(d.finding_id) if d.finding_id else None,
        "status": d.status, "channel": d.channel, "erp_action": d.erp_action,
        "erp_ref": d.erp_ref, "recipient": d.recipient, "locale": d.locale,
    }


@router.get("")
def get_disputes(db: Session = Depends(get_tenant_db)) -> dict:
    return {"disputes": [_out(d) for d in list_disputes(db)]}


@router.post("")
def open_dispute(
    finding_id: str,
    reason: str,
    channel: str = "draft",
    bill_external_id: str | None = None,
    recipient: str | None = None,
    db: Session = Depends(get_tenant_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Abre a mitigação de um achado. Ação externa só com opt-in (auto_mitigation)
    do tenant; senão fica em rascunho. Restrito a Owner/Admin/Controller."""
    require_role(Role.OWNER.value, Role.TENANT_ADMIN.value, Role.CONTROLLER.value)(user)
    d = mitigate_finding(
        db, user.tenant_id, finding_id=finding_id, reason=reason, channel=channel,
        bill_external_id=bill_external_id, recipient=recipient,
    )
    return _out(d)
