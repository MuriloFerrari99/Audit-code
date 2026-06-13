"""Rotas de autenticação (T-051)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text

from app.api.deps import get_current_user
from app.api.schemas import CurrentUser, LoginIn, RefreshIn, TokenOut
from app.core.db import SessionLocal
from app.core.security import (
    decode_token,
    make_access_token,
    make_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _resolve_membership(session, user_id: str, tenant_id: str | None):
    rows = session.execute(
        text("SELECT tenant_id, role FROM membership WHERE user_id = :u"),
        {"u": user_id},
    ).all()
    if not rows:
        return None, None
    if tenant_id:
        for t, r in rows:
            if str(t) == str(tenant_id):
                return str(t), r
        return None, None
    if len(rows) == 1:
        return str(rows[0][0]), rows[0][1]
    return "AMBIGUOUS", None  # precisa escolher tenant_id


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn) -> TokenOut:
    with SessionLocal() as s:
        row = s.execute(
            text("SELECT id, password_hash FROM app_user WHERE email = :e AND is_active"),
            {"e": body.email},
        ).first()
        if not row or not verify_password(body.password, row[1]):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "credenciais inválidas")
        user_id = str(row[0])
        tenant_id, role = _resolve_membership(s, user_id, body.tenant_id)
    if tenant_id == "AMBIGUOUS":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "informe tenant_id (múltiplos tenants)")
    return TokenOut(
        access_token=make_access_token(user_id, tenant_id, role),
        refresh_token=make_refresh_token(user_id),
        tenant_id=tenant_id,
        role=role,
    )


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn) -> TokenOut:
    try:
        claims = decode_token(body.refresh_token)
    except Exception as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh inválido") from e
    if claims.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "tipo de token inválido")
    user_id = claims["sub"]
    with SessionLocal() as s:
        tenant_id, role = _resolve_membership(s, user_id, body.tenant_id)
    return TokenOut(
        access_token=make_access_token(user_id, tenant_id, role),
        refresh_token=make_refresh_token(user_id),
        tenant_id=tenant_id,
        role=role,
    )


@router.get("/me", response_model=CurrentUser)
def me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return user
