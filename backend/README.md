# Backend — Auditoria de Gastos

## Rodar local
```
cp .env.example .env      # na raiz do repo
make up                   # postgres+pgvector, redis, minio, api, worker
make migrate              # aplica migrações (cria tenancy + RLS)
make test                 # roda testes (inclui isolamento multi-tenant)
```

API em http://localhost:8000 (`/healthz`, `/readyz`, `/docs`).

## Estrutura
- `app/core` — config, secrets, db (sessão + RLS por tenant), money, time, logging, errors
- `app/models` — ORM (base + tenancy; canônico nos próximos épicos)
- `app/tenancy` — helpers de RLS
- `app/migrations` — Alembic
- `tests` — inclui `test_isolation.py` (gate de aceite)

Ver `docs/plano-implementacao.md` para o WBS completo.
