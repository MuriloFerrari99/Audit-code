# Deploy & Operação

Stack conteinerizada e cloud-agnóstica (Docker Compose). Roda igual local e em servidor próprio.

## 1. Desenvolvimento local (macOS sem Docker)
```bash
bash scripts/install_runtime.sh     # instala Colima + Docker (pede senha 1x)
cp .env.example .env                # preencher segredos (NÃO versionar)
make up                             # api migra + cria role app_rw + sobe tudo
make seed                           # dados sintéticos (opcional)
make test                           # suíte (inclui isolamento multi-tenant)
```
- API: http://localhost:8000/docs · App: http://localhost:3000 · Métricas: /metrics

## 2. Deploy em servidor
```bash
git clone <repo> && cd audit-code
cp .env.example .env                # preencher via secret manager (ver §4)
docker compose up -d --build        # api roda entrypoint: alembic upgrade + bootstrap_roles
docker compose exec api alembic upgrade head   # (idempotente; o entrypoint já faz)
```
- Pôr um **reverse proxy com TLS** (Caddy/Traefik) na frente de api(8000) e frontend(3000).
- **Backups**: `pg_dump` agendado do volume `pgdata` + restore drill (testar restore!).
- **Worker** (auditoria contínua) sobe junto; intervalo via `SYNC_INTERVAL_MIN`.

## 3. Arquitetura de banco (segurança — C-1)
- O container `api` migra como **role dono** (`DATABASE_URL`) e cria o role da
  aplicação `app_rw` (NOSUPERUSER/NOBYPASSRLS) via `scripts/bootstrap_roles.py`.
- O runtime conecta como **`app_rw`** (`APP_DATABASE_URL`) → RLS realmente aplicado.
- **Nunca** apontar o runtime para o role dono.

## 4. Segredos (fora do repositório)
- `.env` é gitignored. Em produção, injetar via **secret manager** (Vault/Infisical/Docker secrets).
- Por tenant, credenciais do Sienge ficam **criptografadas** em `tenant_secret` (Fernet);
  a chave do app é `APP_SECRET_KEY` (rotacionável).
- Variáveis: ver [.env.example](./.env.example). Sensíveis: `APP_SECRET_KEY`,
  `APP_DB_PASSWORD`, `ANTHROPIC_API_KEY`, `PORTAL_TRANSPARENCIA_KEY`, credenciais Sienge.

## 5. Build reproduzível
- Backend: `requirements.lock` (gerado por `uv pip compile`) — versões fixadas (A-4).
  Atualizar: `uv pip compile pyproject.toml --extra dev -o requirements.lock`.
- Frontend: `package-lock.json` (`npm ci`).

## 6. CI/CD
- [.github/workflows/ci.yml](./.github/workflows/ci.yml): em cada push roda lint, mypy,
  **a suíte com Postgres real** (migra → bootstrap `app_rw` → pytest, inclui isolamento),
  build do frontend, bandit, pip-audit e gitleaks.
- CD (futuro): build das imagens + push + `docker compose pull && up -d` no servidor.

## 7. Rollback
- App: `git revert` + `docker compose up -d --build`.
- Banco: migrações Alembic são reversíveis (`alembic downgrade`); manter backup antes de migrar.

## 8. Observabilidade
- `/healthz` (liveness), `/readyz` (DB), `/metrics` (Prometheus).
- Logs estruturados JSON (sem PII); `audit_log` (trilha do sistema); `dead_letter` (ingestão que falhou).
