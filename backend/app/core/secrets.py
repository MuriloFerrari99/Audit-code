"""SecretProvider (T-021, ADR-11).

Toda credencial (Sienge por tenant, ANTHROPIC_API_KEY, embeddings) é lida
SOMENTE por esta camada — nunca de os.environ direto no código de negócio.

Provedores:
- EnvSecretProvider: variáveis de ambiente (dev / fallback).
- StaticSecretProvider: dict em memória (testar credencial ad-hoc no onboarding).
- DbSecretProvider: tabela tenant_secret, CRIPTOGRAFADA (persiste credencial de
  cliente por tenant). Sabe gravar (set).
- ChainedSecretProvider: tenta DB e cai para env.

Convenção de path: tenant/{tenant_id}/sienge/subdomain|user|password
"""

from __future__ import annotations

import os
import re
from typing import Protocol


class SecretNotFound(KeyError):
    pass


class SecretProvider(Protocol):
    def get(self, path: str) -> str: ...
    def get_optional(self, path: str) -> str | None: ...


def _path_to_env(path: str) -> str:
    return path.replace("/", "__").replace("-", "_").upper()


class _Base:
    def get(self, path: str) -> str:
        val = self.get_optional(path)  # type: ignore[attr-defined]
        if val is None:
            raise SecretNotFound(f"segredo ausente: {path}")
        return val


class EnvSecretProvider(_Base):
    _DEV_FALLBACK = {
        "llm/anthropic/api_key": "ANTHROPIC_API_KEY",
        "embeddings/api_key": "EMBEDDINGS_API_KEY",
    }
    _SIENGE_RE = re.compile(r"^tenant/[^/]+/sienge/(subdomain|user|password)$")

    def get_optional(self, path: str) -> str | None:
        val = os.environ.get(_path_to_env(path))
        if val:
            return val
        fallback = self._DEV_FALLBACK.get(path)
        if fallback:
            return os.environ.get(fallback)
        m = self._SIENGE_RE.match(path)
        if m:
            return os.environ.get(f"SIENGE_DEFAULT_{m.group(1).upper()}")
        return None


class StaticSecretProvider(_Base):
    """Segredos em memória — para validar credenciais ANTES de persistir."""

    def __init__(self, values: dict[str, str]):
        self._values = values

    def get_optional(self, path: str) -> str | None:
        return self._values.get(path)


class DbSecretProvider(_Base):
    """Segredos por tenant na tabela tenant_secret, cifrados (Fernet)."""

    def get_optional(self, path: str) -> str | None:
        from sqlalchemy import text  # import tardio p/ evitar custo no import

        from app.core.crypto import decrypt
        from app.core.db import admin_engine

        try:
            with admin_engine.connect() as conn:
                row = conn.execute(
                    text("SELECT value_enc FROM tenant_secret WHERE path = :p"), {"p": path}
                ).first()
        except Exception:
            return None
        if not row:
            return None
        try:
            return decrypt(row[0])
        except Exception:
            return None

    def set(self, tenant_id: str, path: str, value: str) -> None:
        from sqlalchemy import text

        from app.core.crypto import encrypt
        from app.core.db import admin_engine

        enc = encrypt(value)
        with admin_engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO tenant_secret (id, tenant_id, path, value_enc) "
                    "VALUES (gen_random_uuid(), :t, :p, :v) "
                    "ON CONFLICT (tenant_id, path) DO UPDATE SET value_enc = :v"
                ),
                {"t": tenant_id, "p": path, "v": enc},
            )


class ChainedSecretProvider(_Base):
    def __init__(self, providers: list[SecretProvider]):
        self._providers = providers

    def get_optional(self, path: str) -> str | None:
        for p in self._providers:
            val = p.get_optional(path)
            if val is not None:
                return val
        return None


def get_secret_provider(kind: str = "chained") -> SecretProvider:
    if kind == "env":
        return EnvSecretProvider()
    if kind == "chained":
        return ChainedSecretProvider([DbSecretProvider(), EnvSecretProvider()])
    raise ValueError(f"SecretProvider desconhecido: {kind!r}")
