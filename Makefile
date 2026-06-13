.PHONY: up down logs build test lint fmt typecheck migrate revision seed shell-db

# Infra local
up:        ## sobe o stack (postgres+pgvector, redis, minio, api, worker)
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f
build:
	docker compose build

# Qualidade
lint:
	cd backend && ruff check .
fmt:
	cd backend && ruff format . && ruff check . --fix
typecheck:
	cd backend && mypy app
test:
	cd backend && pytest -q

# Banco
migrate:   ## aplica migrações Alembic
	cd backend && alembic upgrade head
revision:  ## cria migração: make revision m="mensagem"
	cd backend && alembic revision --autogenerate -m "$(m)"
seed:      ## carrega dados sintéticos (formato Sienge)
	cd backend && python -m scripts.seed_synthetic
shell-db:
	docker compose exec postgres psql -U audit -d audit
