# Guia de Deploy — VPS próprio (Docker + Caddy/HTTPS)

> Passo a passo para colocar o SaaS no ar num servidor Linux (Ubuntu 22.04+),
> com HTTPS automático. Cloud-agnóstico: vale p/ Hetzner, DigitalOcean, Contabo,
> AWS Lightsail, etc. Tudo via `docker-compose.prod.yml` + Caddy.

## 0. O que você precisa
- Um **VPS** (mín. 2 vCPU / 4 GB RAM / 40 GB SSD) com Ubuntu 22.04+.
- Um **domínio** (ex.: `suaempresa.com`).
- Acesso SSH ao servidor.

## 1. DNS (no painel do seu domínio)
Crie dois registros **A** apontando para o **IP do servidor**:
```
app.suaempresa.com  ->  <IP_DO_SERVIDOR>
api.suaempresa.com  ->  <IP_DO_SERVIDOR>
```
(Propagação leva minutos. O Caddy só emite o certificado quando o DNS resolver.)

## 2. Servidor: portas e Docker
No firewall do provedor, libere **22 (SSH), 80 e 443**. Depois, via SSH:
```bash
# instala Docker + plugin compose (script oficial)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker   # usar docker sem sudo
docker compose version                            # confirmar
```

## 3. Código + configuração
```bash
git clone <URL_DO_SEU_REPO> audit-code && cd audit-code
cp .env.example .env
nano .env        # preencher (ver abaixo)
```
Preencha no `.env` (o essencial):
```
APP_ENV=production
APP_SECRET_KEY=<gere: openssl rand -hex 32>
POSTGRES_PASSWORD=<senha forte>
APP_DB_PASSWORD=<outra senha forte>
DATABASE_URL=postgresql+psycopg://audit:<POSTGRES_PASSWORD>@postgres:5432/audit
APP_DATABASE_URL=postgresql+psycopg://app_rw:<APP_DB_PASSWORD>@postgres:5432/audit
APP_DOMAIN=app.suaempresa.com
API_DOMAIN=api.suaempresa.com
NEXT_PUBLIC_API_URL=https://api.suaempresa.com
APP_PUBLIC_URL=https://app.suaempresa.com
CORS_ORIGINS=https://app.suaempresa.com
ANTHROPIC_API_KEY=<opcional, p/ os agentes LLM>
PORTAL_TRANSPARENCIA_KEY=<opcional, p/ sanções CEIS/CNEP>
```
> `DATABASE_URL` (dono) e `APP_DATABASE_URL` (app_rw) DEVEM ter senhas/roles
> diferentes — é o que faz o RLS valer (correção C-1). Nunca aponte o runtime
> para o dono.

## 4. Subir
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
O serviço `api` roda sozinho: `alembic upgrade` + cria o role `app_rw` + cadastra
os planos. O Caddy emite o certificado TLS automaticamente.

Verifique:
```bash
docker compose -f docker-compose.prod.yml ps         # tudo "Up"/"healthy"
curl -fsS https://api.suaempresa.com/healthz          # {"status":"ok",...}
```
Abra `https://app.suaempresa.com` (app) e `https://api.suaempresa.com/docs` (API).

## 5. Primeiro acesso e admin de plataforma
1. No app, faça **/signup** (cria seu tenant + usuário).
2. Promova-se a admin de plataforma:
```bash
docker compose -f docker-compose.prod.yml exec api python -m scripts.make_admin seu-email@suaempresa.com
```
Recarregue: a aba **Admin** aparece.

## 6. Backups (faça antes do 1º cliente)
```bash
# dump diário (exemplo de cron às 3h)
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U audit audit | gzip > /var/backups/audit-$(date +%F).sql.gz
```
**Teste o restore** num servidor à parte pelo menos uma vez (backup não testado = não tem backup).

## 7. Atualizar versão
```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```
Migrações rodam sozinhas no boot do `api` (idempotentes).

## 8. Ligar cobrança / mitigação (quando quiser)
Ver [go-live.md](./go-live.md) §"Ligar cobrança real" e §"Ligar mitigação".
Resumo: preencher `BILLING_PROVIDER=stripe` + chaves no `.env`, webhook da Stripe
para `https://api.suaempresa.com/billing/webhook/stripe`; mitigação fica OFF até
opt-in por tenant.

## Troubleshooting
- **Certificado não emite:** DNS ainda não propagou ou portas 80/443 fechadas.
  `docker compose -f docker-compose.prod.yml logs caddy`.
- **API não sobe:** `... logs api` — geralmente `.env` (senha do banco) incorreto.
- **CORS no app:** `CORS_ORIGINS` precisa ser exatamente a URL https do app.
