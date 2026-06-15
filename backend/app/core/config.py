"""Configuração tipada da aplicação (T-020).

Lê de variáveis de ambiente / .env. Segredos sensíveis NÃO são lidos aqui
diretamente no código de negócio — passam pelo SecretProvider (ADR-11).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "local"
    app_secret_key: str = "dev-only-change-me"
    log_level: str = "INFO"
    business_timezone: str = "America/Sao_Paulo"

    # Banco
    # database_url = role DONO (migrações + operações de plataforma). É superusuário
    # no Postgres oficial → NÃO deve ser usado pelo runtime (superuser ignora RLS).
    database_url: str = "postgresql+psycopg://audit:audit@localhost:5432/audit"
    # app_database_url = role da APLICAÇÃO (NOSUPERUSER, NOBYPASSRLS). É com ele
    # que o runtime acessa dado de cliente, para o RLS valer de fato (C-1).
    app_database_url: str = "postgresql+psycopg://app_rw:app_rw@localhost:5432/audit"
    # senha do role de aplicação, usada pelo bootstrap p/ criar/rotacionar o role.
    app_db_password: str = "app_rw"
    db_owner: str = "audit"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Object store
    s3_endpoint: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket: str = "audit-evidence"

    # Secret provider (ADR-11)
    secret_provider: str = "env"

    # LLM (ADR-12) — valores reais via SecretProvider
    llm_model_strong: str = "claude-opus-4-8"
    llm_model_cheap: str = "claude-haiku-4-5-20251001"
    llm_tenant_token_budget: int = 2_000_000

    # Embeddings
    embeddings_provider: str | None = None
    embeddings_model: str | None = None

    # Cobrança (Fase 2). billing_provider: none|stripe. Chaves via SecretProvider/env.
    billing_provider: str = "none"
    stripe_api_key: str | None = None
    stripe_webhook_secret: str | None = None

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
