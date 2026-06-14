"""Bootstrap do role de aplicação (C-1). Roda como DONO (admin_engine).

Cria/atualiza `app_rw` SEM superusuário e SEM BYPASSRLS, e concede só CRUD nas
tabelas — para que o RLS seja efetivamente aplicado ao runtime. Idempotente.

Uso (no container): python -m scripts.bootstrap_roles
"""

from __future__ import annotations

from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import admin_engine
from app.core.logging import get_logger

log = get_logger("bootstrap")


def bootstrap_roles() -> None:
    s = get_settings()
    pw = s.app_db_password.replace("'", "''")  # escapa aspas simples
    owner = s.db_owner
    role = "app_rw"

    with admin_engine.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": role}
        ).first()
        if exists:
            conn.execute(text(
                f"ALTER ROLE {role} WITH LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB "
                f"NOCREATEROLE PASSWORD '{pw}'"
            ))
        else:
            conn.execute(text(
                f"CREATE ROLE {role} WITH LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB "
                f"NOCREATEROLE PASSWORD '{pw}'"
            ))

        # privilégios mínimos: CRUD nas tabelas existentes + futuras
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(text(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {role}"
        ))
        conn.execute(text(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}"))
        conn.execute(text(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {owner} IN SCHEMA public "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {role}"
        ))
        conn.execute(text(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE {owner} IN SCHEMA public "
            f"GRANT USAGE, SELECT ON SEQUENCES TO {role}"
        ))
    log.info("bootstrap.roles.done", role=role)


if __name__ == "__main__":
    bootstrap_roles()
    print("role app_rw criado/atualizado (NOSUPERUSER, NOBYPASSRLS) + grants aplicados.")
