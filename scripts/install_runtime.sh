#!/usr/bin/env bash
# Instala um runtime de container (Colima + Docker CLI) no macOS Apple Silicon,
# sem Docker Desktop/GUI. Rode UMA vez, numa aba do terminal. Vai pedir sua
# senha de admin (sudo) — isso é normal e necessário.
#
#   bash "scripts/install_runtime.sh"
#
# Depois: make up && make migrate && docker compose exec api python -m scripts.sync_alumbra 300
set -e

echo "==> 1/4 Homebrew"
if ! command -v brew >/dev/null 2>&1; then
  echo "Instalando Homebrew (vai pedir sua senha)..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
# garante o brew no PATH desta sessão (Apple Silicon)
if [ -x /opt/homebrew/bin/brew ]; then eval "$(/opt/homebrew/bin/brew shellenv)"; fi

echo "==> 2/4 Colima + Docker CLI + docker-compose"
brew install colima docker docker-compose

echo "==> 3/4 Iniciando a máquina de containers (Colima)"
colima start --cpu 2 --memory 4 --disk 20 || colima start

echo "==> 4/4 Verificando"
docker version && docker compose version && docker info >/dev/null && echo "OK: Docker pronto."

cat <<'EOF'

============================================================
PRONTO. Agora, na pasta do projeto:

  make up            # sobe postgres+pgvector, redis, minio, api, worker, frontend
  make migrate       # cria as tabelas
  docker compose exec api python -m scripts.sync_alumbra 300

Painel: http://localhost:3000  (login: founder@cliente.com / audit12345)
============================================================
EOF
