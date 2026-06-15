#!/usr/bin/env bash
# Entrypoint da API: migra (como DONO) + cria o role de aplicação (app_rw, sem
# superusuário) + sobe o processo (que conecta como app_rw, com RLS valendo).
set -e

echo "[entrypoint] migrando schema (role dono)..."
for i in $(seq 1 30); do
  if alembic upgrade head; then break; fi
  echo "[entrypoint] banco indisponível, retry ($i)..."; sleep 2
done

echo "[entrypoint] bootstrap do role de aplicação (app_rw)..."
python -m scripts.bootstrap_roles

echo "[entrypoint] bootstrap do catálogo de planos..."
python -m scripts.bootstrap_plans

echo "[entrypoint] iniciando: $*"
exec "$@"
