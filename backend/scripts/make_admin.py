"""Promove um usuário a admin de plataforma (is_superuser=True).

Uso: python -m scripts.make_admin email@empresa.com
"""

from __future__ import annotations

import sys

from sqlalchemy import text

from app.core.db import admin_session


def make_admin(email: str) -> bool:
    with admin_session() as s:
        r = s.execute(
            text("UPDATE app_user SET is_superuser = true WHERE email = :e"), {"e": email}
        )
        return bool(r.rowcount)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("uso: python -m scripts.make_admin email@empresa.com")
        raise SystemExit(2)
    ok = make_admin(sys.argv[1])
    print(f"{sys.argv[1]}: {'agora é admin de plataforma' if ok else 'não encontrado'}")
