.PHONY: up down logs build test lint fmt typecheck migrate bootstrap revision seed sync shell-db

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

# Banco (rodam DENTRO do container — a API já migra+bootstrap no `make up`)
migrate:   ## aplica migrações Alembic (role dono)
	docker compose exec api alembic upgrade head
bootstrap: ## cria/atualiza o role de aplicação app_rw (C-1)
	docker compose exec api python -m scripts.bootstrap_roles
revision:  ## cria migração: make revision m="mensagem"
	docker compose exec api alembic revision --autogenerate -m "$(m)"
seed:      ## carrega dados sintéticos (formato Sienge)
	docker compose exec api python -m scripts.seed_synthetic
sync:      ## sync real do Sienge (Alumbra): make sync n=300
	docker compose exec api python -m scripts.sync_alumbra $(or $(n),300)
test:      ## roda a suíte dentro do container (inclui isolamento)
	docker compose exec api pytest -q
shell-db:
	docker compose exec postgres psql -U audit -d audit
