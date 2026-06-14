"""Acesso a banco + fixação de tenant para RLS (T-022, ADR-08, C-1).

Dois engines, de propósito:
- `engine` (app_rw): role NOSUPERUSER/NOBYPASSRLS. TODO acesso a dado de cliente
  passa por aqui, dentro de `tenant_session()`, que seta `app.current_tenant`.
  Como NÃO é superusuário, o RLS é REALMENTE aplicado (correção do C-1).
- `admin_engine` (dono): só para migrações/bootstrap e tabelas de plataforma
  sem RLS (ex.: criar tenant). Nunca usado para ler dado de cliente.

Jobs de background DEVEM abrir a sessão com o tenant explícito.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.errors import TenantContextMissing
from app.core.logging import tenant_id_var

_settings = get_settings()

# Engine de APLICAÇÃO (RLS valendo) — role app_rw.
engine = create_engine(_settings.app_database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False, future=True)

# Engine DONO (migrações / plataforma). Não acessa dado de cliente.
admin_engine = create_engine(_settings.database_url, pool_pre_ping=True, future=True)
AdminSessionLocal = sessionmaker(
    bind=admin_engine, class_=Session, expire_on_commit=False, future=True
)


@contextmanager
def tenant_session(tenant_id: str) -> Iterator[Session]:
    """Sessão transacional com o tenant fixado (RLS ativo)."""
    if not tenant_id:
        raise TenantContextMissing("tenant_session requer tenant_id")
    session = SessionLocal()
    token = tenant_id_var.set(tenant_id)
    try:
        # SET LOCAL vale só para esta transação; usa parâmetro via set_config.
        session.execute(
            text("SELECT set_config('app.current_tenant', :tid, true)"),
            {"tid": str(tenant_id)},
        )
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        tenant_id_var.reset(token)


@contextmanager
def admin_session() -> Iterator[Session]:
    """Sessão do role DONO para operações de plataforma (criar tenant, ETL de
    referência pública). NÃO usar para ler dado de cliente — é o role dono e
    pode ignorar RLS. Tabelas de cliente devem ser acessadas via tenant_session."""
    session = AdminSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def db_healthy() -> bool:
    try:
        with admin_session() as s:
            s.execute(text("SELECT 1"))
        return True
    except Exception:  # pragma: no cover
        return False
