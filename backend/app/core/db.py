"""Acesso a banco + fixação de tenant para RLS (T-022, ADR-08).

A role da aplicação NÃO tem BYPASSRLS. Toda unidade de trabalho sobre dado de
cliente roda dentro de `tenant_session(tenant_id)`, que executa
`SET LOCAL app.current_tenant` na transação. As policies RLS filtram por
`current_setting('app.current_tenant')`.

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
engine = create_engine(_settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False, future=True)


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
    """Sessão SEM tenant para operações de plataforma (criar tenant, migrações
    de controle). Não acessa tabelas de dado de cliente protegidas por RLS sem
    um tenant setado — use com cuidado."""
    session = SessionLocal()
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
