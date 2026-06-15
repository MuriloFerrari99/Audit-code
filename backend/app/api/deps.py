"""Dependências de API: autenticação, contexto de tenant e RBAC (T-052)."""

from __future__ import annotations

from collections.abc import Iterator

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.schemas import CurrentUser
from app.core.db import SessionLocal
from app.core.logging import tenant_id_var
from app.core.security import decode_token


def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token ausente")
    token = authorization.split(" ", 1)[1]
    try:
        claims = decode_token(token)
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token expirado") from e
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token inválido") from e
    if claims.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "tipo de token inválido")
    email = ""
    is_admin = False
    with SessionLocal() as s:
        row = s.execute(
            text("SELECT email, is_superuser FROM app_user WHERE id = :id AND is_active"),
            {"id": claims["sub"]},
        ).first()
        if row:
            email, is_admin = row[0], bool(row[1])
    if not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "usuário inválido")
    return CurrentUser(
        user_id=claims["sub"],
        email=email,
        tenant_id=claims.get("tenant_id"),
        role=claims.get("role"),
        is_platform_admin=is_admin,
    )


def get_tenant_db(user: CurrentUser = Depends(get_current_user)) -> Iterator[Session]:
    """Sessão com RLS fixado no tenant do token. Toda rota de dado de cliente
    depende daqui — garante isolamento."""
    if not user.tenant_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "token sem tenant")
    session = SessionLocal()
    token = tenant_id_var.set(user.tenant_id)
    try:
        session.execute(
            text("SELECT set_config('app.current_tenant', :tid, true)"),
            {"tid": str(user.tenant_id)},
        )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        tenant_id_var.reset(token)


def require_role(*roles: str):
    def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if roles and user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "permissão insuficiente")
        return user

    return _checker


def require_platform_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Acesso à plataforma (cross-tenant). Só usuários staff (is_superuser)."""
    if not user.is_platform_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "acesso restrito à plataforma")
    return user
