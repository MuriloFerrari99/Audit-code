# Checklist de Go-Live

> Portão de produção da auditoria ([auditoria-codigo-2026-06-14.md](./auditoria-codigo-2026-06-14.md) §8).
> Marcar PRONTO só com TUDO verde. Estado em 2026-06-15.

## Portão (bloqueia cliente pagante)

| # | Requisito | Estado | Observação |
|---|-----------|:------:|-------------|
| 1 | Zero achados CRÍTICOS | 🟢 | C-1 corrigido e provado no CI; C-3 (credencial Sienge) rotacionado |
| 2 | Isolamento multi-tenant **provado por teste** | 🟢 | `test_isolation` sob `app_rw` verde no CI |
| 3 | Nenhum segredo no repo/histórico | 🟢 | `.env` gitignored; gitleaks no CI |
| 4 | Suíte passa e cobre caminhos críticos | 🟢 | 78 testes verdes em Postgres real (CI) |
| 5 | Read-only no ERP garantido | 🟢 | leitura por design; escrita (mitigação) é opt-in + log-only por padrão |

## Configuração de produção (no servidor)

1. **Compose de produção:** `docker compose -f docker-compose.prod.yml up -d --build`
   (sem `--reload`/mount; `restart: unless-stopped`; healthchecks). O `api` roda
   `entrypoint.sh` → `alembic upgrade` + `bootstrap_roles` + `bootstrap_plans`.
2. **`.env` via secret manager** (não versionar). Conferir contra [.env.example](../.env.example):
   `DATABASE_URL` (dono) ≠ `APP_DATABASE_URL` (app_rw); `APP_SECRET_KEY`, `APP_DB_PASSWORD`.
3. **Reverse proxy com TLS** (Caddy/Traefik) na frente de api(8000)/frontend(3000);
   setar `APP_PUBLIC_URL`, `NEXT_PUBLIC_API_URL`, `CORS_ORIGINS` para o domínio real.
4. **Promover admin de plataforma:** `docker compose exec api python -m scripts.make_admin <email>`.
5. **Backups** do Postgres (`pg_dump` do volume `pgdata`) + **restore drill**.
6. **Object storage gerenciado** (S3) no lugar do MinIO: variáveis `S3_*`.

## Ligar cobrança real (Stripe) — quando for faturar
- Criar Products/Prices na Stripe; gravar `stripe_price_id` em `plan.features` de cada plano.
- `BILLING_PROVIDER=stripe`, `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`.
- Webhook da Stripe → `POST /billing/webhook/stripe`.
- Definir o **% de gainshare** dos planos (decisão comercial; hoje em branco).

## Ligar mitigação automática (Executor) — opcional, alto risco
- **Default seguro** (`ERP_PROVIDER=log_only`): nada sai para fora.
- Para agir: homologar `SiengeErpAdapter.block_payment`, `ERP_PROVIDER=sienge`
  **e** `tenant.auto_mitigation=true` por cliente (opt-in explícito).

## Antes do 1º cliente pagante
- **DPA/contrato + base legal LGPD** revisados.
- Posicionamento "auditoria gerencial/advisory" (ver fim do doc).

## Já endurecido (feito)
- C-1 RLS: runtime usa `app_rw` (sem superusuário) — RLS aplicado de fato.
- A-2: worker de auditoria contínua (APScheduler).
- A-3: `dead_letter` — ingestão nunca falha em silêncio.
- A-4: `requirements.lock` (backend) + `package-lock.json` (frontend) — build reproduzível.
- M-1: CI com lint + types + suíte (Postgres real) + scanners.
- Qualidade dos achados: higiene de dados + filtros por natureza + score de confiança + calibração por tenant.
- Fase 2: planos/assinatura/uso + gainshare + Stripe (adapter agnóstico) + painel admin.
- Fase Agêntica: CDM + Ports (hexagonal) + OpenSquad (Extrator→Enriquecedor→Auditor→Executor)
  + prontuário (`agent_reasoning_log`) + disputas + citações legais + event-driven (outbox/worker).
- Mitigação segura por padrão (log-only) + opt-in por tenant (`auto_mitigation`).

## Features gated (não bloqueiam go-live; ligam com credencial)
- **I1** fornecedor sancionado → chave gratuita do Portal da Transparência.
- **F6** nota fria/SEFAZ → certificado digital A1/A3 do cliente.
- **Open Finance** (conta divergente/conciliação) → agregador (Pluggy/Belvo) + consentimento bancário.

## Posicionamento (não esquecer)
- "Auditoria **gerencial** de gastos" (spend intelligence), **advisory**, humano decide.
- Nunca "auditoria independente" (termo regulado CVM/CFC).
