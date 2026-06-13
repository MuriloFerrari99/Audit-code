"""SecretProvider (T-021, ADR-11).

Toda credencial (Sienge por tenant, ANTHROPIC_API_KEY, embeddings) é lida
SOMENTE por esta camada — nunca de os.environ direto no código de negócio.
Local usa EnvSecretProvider; em servidor troca-se por Vault/File sem mudar o
código que consome.

Convenção de path (namespaced por tenant):
    tenant/{tenant_id}/sienge/subdomain | user | password
    llm/anthropic/api_key
    embeddings/api_key
"""

from __future__ import annotations

import os
from typing import Protocol


class SecretNotFound(KeyError):
    pass


class SecretProvider(Protocol):
    def get(self, path: str) -> str: ...
    def get_optional(self, path: str) -> str | None: ...


def _path_to_env(path: str) -> str:
    # tenant/abc/sienge/user -> TENANT__ABC__SIENGE__USER
    return path.replace("/", "__").replace("-", "_").upper()


class EnvSecretProvider:
    """Lê segredos de variáveis de ambiente. Para dev local.

    Tenta primeiro a forma namespaced (TENANT__{ID}__SIENGE__USER) e, como
    conveniência de dev, cai para variáveis simples conhecidas.
    """

    _DEV_FALLBACK = {
        "llm/anthropic/api_key": "ANTHROPIC_API_KEY",
        "embeddings/api_key": "EMBEDDINGS_API_KEY",
    }

    def get_optional(self, path: str) -> str | None:
        val = os.environ.get(_path_to_env(path))
        if val:
            return val
        fallback = self._DEV_FALLBACK.get(path)
        if fallback:
            return os.environ.get(fallback)
        return None

    def get(self, path: str) -> str:
        val = self.get_optional(path)
        if val is None:
            raise SecretNotFound(f"segredo ausente: {path}")
        return val


def get_secret_provider(kind: str = "env") -> SecretProvider:
    if kind == "env":
        return EnvSecretProvider()
    raise ValueError(f"SecretProvider desconhecido: {kind!r} (impl futura: vault/file)")
