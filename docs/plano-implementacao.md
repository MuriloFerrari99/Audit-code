# Plano de Implementação do MVP (WBS)

> Decomposição granular para **não errar na construção**. Cada tarefa tem **ID**, **dependências**, **definição de pronto (DoD)** e marca de **bloqueio** quando depende de input do founder. Ordem de construção respeita as dependências. Os ADRs referenciados estão em [revisao-arquitetura.md](./revisao-arquitetura.md).

## Legenda

- 🟢 **livre** — posso construir já (sem credencial/PoC).
- 🔒 **bloqueado** — precisa de input do founder (Q#) — ver [perguntas-abertas.md](./perguntas-abertas.md).
- 🧪 DoD inclui teste automatizado.

## Dependências entre épicos

```
E0 → E1 → E2 → E3 → E4 ─┬─► E6 (conector)  ─┐
                         ├─► E7 (SINAPI)     ├─► E9 (regras) ─► E10 (achados) ─► E11 (revisão+ledger)
                         └─► E8 (catálogo/ML)┘                          │
E2 → E5 (auth) ───────────────────────────────────────────────────────┤
E10 → E12 (agentes) ; E10/E11 → E13 (API) → E14 (frontend) ; E10 → E15 (alertas)
E2 → E16 (observabilidade/ops) ; E4 → E17 (seed sintético + E2E)
```

---

## E0 — Fundação de repositório e tooling 🟢

| ID | Tarefa | Dep | DoD |
|----|--------|-----|-----|
| T-001 | `git init`, estrutura de pastas (backend/frontend/docs/reference-data/scripts) | — | árvore criada, `git status` limpo após 1º commit |
| T-002 | `.gitignore` (.env*, segredos, certs, __pycache__, node_modules, .venv) | T-001 | nenhum padrão sensível versionável |
| T-003 | Gerência de deps backend (`pyproject.toml` + uv/poetry), versões fixadas | T-001 | `install` reproduzível |
| T-004 | Lint/format/types (ruff + black + mypy) + config | T-003 | `make lint` passa |
| T-005 | `.pre-commit-config.yaml` com **secret scanning** (detect-secrets/gitleaks) + lint | T-004 | hook bloqueia segredo commitado 🧪 |
| T-006 | `Makefile` (up, down, test, lint, migrate, seed, fmt) | T-003 | alvos funcionam |

## E1 — Infra local conteinerizada 🟢

| ID | Tarefa | Dep | DoD |
|----|--------|-----|-----|
| T-010 | `docker-compose.yml`: postgres(+pgvector), redis, minio | T-006 | `make up` sobe os 4 serviços saudáveis |
| T-011 | `Dockerfile` backend (api) e worker | T-010 | imagens buildam |
| T-012 | `.env.example` (nomes de var, zero segredo) | T-010 | cópia p/ `.env` sobe o stack |
| T-013 | Reverse proxy local + TLS dev (Caddy/Traefik) — opcional MVP | T-010 | acessível via https local |

## E2 — Plataforma core 🟢

| ID | Tarefa | Dep | DoD |
|----|--------|-----|-----|
| T-020 | `core/config.py` (Pydantic Settings, lê via SecretProvider) | T-003 | config tipada carrega |
| T-021 | `SecretProvider` (interface + `EnvSecretProvider`) — ADR-11 | T-020 | segredo lido só pelo provider 🧪 |
| T-022 | `core/db.py`: engine, sessão, **SET app.current_tenant por request/job** — ADR-08 | T-010 | sessão seta tenant 🧪 |
| T-023 | `core/money.py`: tipo `Money` (Decimal/NUMERIC), arredondamento — ADR-04 | T-003 | proibido float; testes de arredondamento 🧪 |
| T-024 | `core/time.py`: utilidades tz negócio/UTC, janelas, período mensal — ADR-05 | T-003 | testes de janela/fuso 🧪 |
| T-025 | `core/logging.py`: structlog JSON + contextvars (request_id, tenant_id) — ADR-18 | T-020 | log estruturado sem PII |
| T-026 | `core/errors.py`: taxonomia (dado/transitório/programação) — ADR-15 | T-020 | classes + handlers |
| T-027 | App FastAPI mínimo + `/healthz` `/readyz` | T-020..T-026 | sobe e responde |

## E3 — Multi-tenancy e isolamento 🟢

| ID | Tarefa | Dep | DoD |
|----|--------|-----|-----|
| T-030 | Tabelas `tenant`, `company`, `project` + migração | T-022, T-040 | criadas |
| T-031 | Política **RLS** em toda tabela de dado de cliente | T-030 | policies ativas |
| T-032 | Contexto de tenant (middleware/dependency) seta `app.current_tenant` | T-022 | resolvido por request |
| T-033 | **Suíte de teste de isolamento** (tenant A não lê/escreve B) — gate de aceite | T-031 | testes provam isolamento 🧪 |

## E4 — Modelo canônico, raw, histórico, outbox 🟢

| ID | Tarefa | Dep | DoD |
|----|--------|-----|-----|
| T-040 | Setup **Alembic** + 1ª migração base — ADR-19 | T-022 | `make migrate` aplica |
| T-041 | `raw_record` (landing append-only) — ADR-06 | T-040 | grava payload bruto |
| T-042 | `entity_history` (snapshots append-only) — ADR-20 | T-040 | versão por mudança |
| T-043 | `outbox_event` + worker consumidor — ADR-01 | T-040 | evento na mesma tx do dado 🧪 |
| T-044 | Entidades canônicas da cadeia (creditor, budget_item, quotation, purchase_request(+item), purchase_order(+item, authorization), invoice/delivery, bill/payment) | T-030 | schemas + migração |
| T-045 | Campos comuns (tenant/company/project, country/currency, source, content_hash, version) + chave natural única | T-044 | upsert idempotente 🧪 |
| T-046 | `catalog_item`, `item_mapping` (pgvector) — ADR-16 | T-044 | criadas |
| T-047 | `finding`, `finding_evidence`, `finding_review`, `rule_config`, `value_ledger`, `audit_log`, `membership` | T-044 | criadas; `finding` com `dedup_key`, `config/reference_snapshot` |

## E5 — Auth e RBAC 🟢

| ID | Tarefa | Dep | DoD |
|----|--------|-----|-----|
| T-050 | `user`, `membership` + senha Argon2 — ADR-08 | T-047 | usuário criado |
| T-051 | Login/refresh (JWT/cookie httpOnly) | T-050 | fluxo de sessão 🧪 |
| T-052 | RBAC (papéis) + escopo por empresa/obra | T-051 | autorização por papel 🧪 |
| T-053 | SSO (OIDC/SAML) — **stub/interface**; impl na Fase 1 | T-051 | interface pronta |

## E6 — Framework de conector + Sienge

| ID | Tarefa | Dep | Bloq | DoD |
|----|--------|-----|------|-----|
| T-060 | Interface `SourceConnector` (auth, list, pull, normalize, health) | T-044 | 🟢 | contrato + teste |
| T-061 | HTTP client: rate limit (Redis token bucket), retry/backoff/jitter, circuit breaker — ADR-10/15 | T-060 | 🟢 | testes com servidor fake 🧪 |
| T-062 | Watermark + paginação por cursor + idempotência | T-061 | 🟢 | retoma sem duplicar 🧪 |
| T-063 | Conector Sienge: auth Basic por subdomínio (via SecretProvider) | T-061 | 🔒 Q1/Q7 | autentica no ambiente real |
| T-064 | Pull dos 7 endpoints + dead-letter | T-063 | 🔒 Q1 | puxa entidades reais |
| T-065 | Normalização campo-a-campo → canônico (mapa fixado contra resposta real) | T-064 | 🔒 Q1 | mapa em [conector-sienge.md](./conector-sienge.md) §6 completo |
| T-066 | **Fixtures gravadas** (sanitizadas) + testes de replay — ADR-13 | T-062 | 🟢 | lógica testada sem credencial 🧪 |
| T-067 | Scheduler (APScheduler) + jobs de sync incremental por tenant + advisory lock | T-062 | 🟢 | sync agendado idempotente 🧪 |

## E7 — Dados de referência (SINAPI/CUB) 🟢

| ID | Tarefa | Dep | DoD |
|----|--------|-----|-----|
| T-070 | ETL SINAPI (download mensal → tabela de referência por UF/período) | T-044 | importa SINAPI |
| T-071 | CUB por UF (sanity) | T-070 | importado |
| T-072 | Resolver de referência por `(catalog_item, UF, período)` | T-070 | retorna referência + metadados (camada/fonte) |

## E8 — Catálogo e casamento de insumo (ML) 🟢

| ID | Tarefa | Dep | DoD |
|----|--------|-----|-----|
| T-080 | Seed do catálogo a partir do SINAPI — ADR-16 | T-046, T-070 | catálogo semeado |
| T-081 | Normalização determinística (unidades, bitolas, sinônimos) | T-046 | normaliza descrição 🧪 |
| T-082 | Embeddings via API externa (SecretProvider) + cache por hash — ADR-12 | T-021 | embeda + cacheia |
| T-083 | Match por similaridade (pgvector) + limiares (auto/ambíguo/humano) | T-082 | match com confiança 🧪 |
| T-084 | Fila humana de casamento ambíguo → rótulo | T-083, T-047 | decisão vira `item_mapping` |

## E9 — Motor de regras + 6 regras

| ID | Tarefa | Dep | Bloq | DoD |
|----|--------|-----|------|-----|
| T-090 | Engine: contrato `Rule`, registry, resolução de config (default→tenant) — ADR-07 | T-047 | 🟢 | engine roda regra dummy 🧪 |
| T-091 | `dedup_key` + upsert idempotente de achado — ADR-03 | T-090 | 🟢 | re-run não duplica 🧪 |
| T-092 | Snapshot de config+referência no achado — ADR-07 | T-090, T-072 | 🟢 | achado reprodutível |
| T-093 | **Incorporar/refatorar o PoC** nas 6 regras (R1..R6) | T-090 | 🔒 Q2 | 6 regras portadas |
| T-094 | **Golden tests** das 6 regras (cenário→achados esperados, R$, evidência) — ADR-14 | T-093 | 🟢* | paridade com o PoC 🧪 (*esqueleto livre; assert final após Q2) |
| T-095 | Cálculo de R$ exposto (Money) + evidência citável por regra | T-093 | 🔒 Q2 | cada achado com R$ + evidência |
| T-096 | Reavaliação incremental disparada pelo outbox | T-090, T-043 | 🟢 | só recalcula o afetado 🧪 |

## E10 — Achados, evidência, ciclo de vida

| ID | Tarefa | Dep | DoD |
|----|--------|-----|-----|
| T-100 | Persistência de achado + evidência ligada às linhas canônicas | T-091 | evidência estrutural |
| T-101 | **Máquina de estados** do achado — ADR-02 | T-100 | transições válidas 🧪 |
| T-102 | Reprocesso preserva rótulo humano (sticky) + SUPERSEDED por versão de regra | T-101 | rótulo nunca apagado 🧪 |
| T-103 | Triador (priorização) — ver E12 | T-100 | fila ordenada |

## E11 — Revisão humana, rótulo e ledger de gainshare

| ID | Tarefa | Dep | Bloq | DoD |
|----|--------|-----|------|-----|
| T-110 | Fluxo aceitar/descartar/escalar → `finding_review` (rótulo) | T-101 | 🟢 | decisão persistida 🧪 |
| T-111 | `value_ledger`: exposto→validado (MVP) — ADR-02/[gtm.md](./gtm.md) | T-110 | 🟢 | ledger registra |
| T-112 | Baseline congelado + evidência no ledger (anti-gaming) | T-111 | 🟢 | baseline imutável |
| T-113 | True-up (reversão) | T-111 | 🟢 | estorno por linha 🧪 |
| T-114 | Realizado (aceito+sanado) + lookback | T-111 | 🔒 Q3 | parâmetros comerciais |

## E12 — Agentes (Claude) 🟢 (config: 🔒 Q nenhuma; usa SecretProvider)

| ID | Tarefa | Dep | DoD |
|----|--------|-----|-----|
| T-120 | Camada de cliente LLM (Anthropic SDK) + roteamento de modelo + budget/PII — ADR-12 | T-021 | chamada com guardrails 🧪 |
| T-121 | Investigador (dossiê da cadeia, read-only) | T-100, T-120 | dossiê citável |
| T-122 | Casador (desambiguação) → integra E8 | T-083, T-120 | match proposto |
| T-123 | Triador (priorização materialidade×confiança) | T-100, T-120 | fila priorizada |
| T-124 | Narrador (resumo executivo + relatório mensal) | T-111, T-120 | relatório gerado |

## E13 — API 🟢

| ID | Tarefa | Dep | DoD |
|----|--------|-----|-----|
| T-130 | Endpoints: findings (lista/detalhe/evidência), review, config, reports, SSE feed — ADR-09 | T-110 | OpenAPI + testes 🧪 |
| T-131 | Auth nos endpoints + escopo por papel/obra | T-052 | autorizado 🧪 |
| T-132 | Paginação, filtros (obra, severidade, status, período) | T-130 | filtros funcionam |

## E14 — Frontend (Claude Design)

| ID | Tarefa | Dep | DoD |
|----|--------|-----|-----|
| T-140 | Design do dashboard via **Claude Design** | T-130 | telas aprovadas |
| T-141 | Next.js + TS: fila de achados priorizada | T-140 | lista consome API |
| T-142 | Dossiê de evidência + R$ + referência | T-141 | detalhe completo |
| T-143 | Fluxo de revisão (aceitar/descartar/escalar) | T-141 | gera rótulo |
| T-144 | Config por tenant + resumo executivo + tempo real (SSE) | T-141 | atualiza ao vivo |

## E15 — Alertas (e-mail) 🟢

| ID | Tarefa | Dep | DoD |
|----|--------|-----|-----|
| T-150 | Serviço de e-mail (provider abstrato) + templates | T-100 | envia alerta |
| T-151 | Regras de disparo (severidade/materialidade) | T-150 | alerta no evento certo |

## E16 — Observabilidade e ops 🟢

| ID | Tarefa | Dep | DoD |
|----|--------|-----|-----|
| T-160 | `/metrics` Prometheus + métricas-chave — ADR-18 | T-027 | métricas expostas |
| T-161 | `audit_log` append-only ligado a leituras/achados/revisões/agentes | T-047 | trilha imutável 🧪 |
| T-162 | Backups (`pg_dump` agendado) + restore drill — ADR-19 | T-010 | backup/restore testado |

## E17 — Seed sintético + E2E 🟢 / 🔒

| ID | Tarefa | Dep | Bloq | DoD |
|----|--------|-----|------|-----|
| T-170 | Seed sintético no formato Sienge (reaproveitar o do PoC) | T-044 | 🔒 Q2 (dados do PoC) / 🟢 (gerar próprio) | dataset carrega |
| T-171 | Smoke E2E com sintético: ingest→regras→achado→revisão→ledger→relatório | T-110, T-124, T-170 | 🟢 | pipeline ponta-a-ponta passa 🧪 |
| T-172 | Smoke com dado real do Sienge | T-065 | 🔒 Q1 | pipeline com base real |

---

## Caminho crítico e o que construo já

**Sequência sem bloqueio (posso fazer agora):**
`E0 → E1 → E2 → E3 → E4 → E5 → E9(framework T-090/091/092/096) + E7 + E8 + E6(framework T-060/061/062/066/067) + E10 + E11(T-110..113) + E12 + E13 + E15 + E16 → E17(T-170 próprio/T-171)`

**Destrava com input do founder:**
- **Q1/Q7 (credenciais Sienge):** T-063, T-064, T-065, T-172.
- **Q2 (motor do PoC):** T-093, T-094 (assert final), T-095, T-170 (dados do PoC).
- **Q3 (gainshare %):** T-114.

Ou seja: construo **toda a espinha** (infra, isolamento, canônico, motor de regras, achados, revisão, ledger, agentes, API, alertas, observabilidade) com **dados sintéticos próprios**, e encaixo o conector real + o seu PoC quando você me passar credenciais e o código — sem rework, porque o contrato (`SourceConnector`, `Rule`, golden tests) já estará pronto para recebê-los.

## Ordem de execução imediata (próximos commits)

1. T-001..T-006 (repo + tooling)
2. T-010..T-012 (compose)
3. T-020..T-027 (core)
4. T-040, T-030..T-033 (alembic + tenancy + **teste de isolamento**)
5. T-041..T-047 (canônico + raw + history + outbox + finding)
