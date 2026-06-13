"""Segurança: hash de senha (Argon2) e tokens JWT (ADR-08, T-051)."""

from __future__ import annotations

from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings
from app.core.timeutils import now_utc

_ph = PasswordHasher()
_ALG = "HS256"

ACCESS_TTL = timedelta(minutes=30)
REFRESH_TTL = timedelta(days=14)


def hash_password(raw: str) -> str:
    return _ph.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, raw)
    except VerifyMismatchError:
        return False


def _encode(claims: dict, ttl: timedelta, token_type: str) -> str:
    now = now_utc()
    payload = {**claims, "type": token_type, "iat": now, "exp": now + ttl}
    return jwt.encode(payload, get_settings().app_secret_key, algorithm=_ALG)


def make_access_token(user_id: str, tenant_id: str | None, role: str | None) -> str:
    return _encode({"sub": user_id, "tenant_id": tenant_id, "role": role}, ACCESS_TTL, "access")


def make_refresh_token(user_id: str) -> str:
    return _encode({"sub": user_id}, REFRESH_TTL, "refresh")


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_settings().app_secret_key, algorithms=[_ALG])
