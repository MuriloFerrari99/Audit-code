# Revisão de Arquitetura (pré-construção)

> Revisão crítica de toda a arquitetura **antes de escrever código**, para não errar na construção. Cada item é uma decisão registrada (ADR) que **resolve um buraco** que só apareceria na hora de implementar. Onde a decisão refina/corrige um doc anterior, está indicado. Esta é a referência autoritativa para os ADRs; os docs de origem continuam válidos no resto.

## Buracos encontrados na 1ª versão (resumo honesto)

A arquitetura original estava correta no **quê**, mas vaga no **como** em pontos que quebram a construção se deixados implícitos:

1. **Eventos** ("dado mudou → reavalia regra") sem mecanismo definido → risco de evento perdido / regra não reavaliada.
2. **Ciclo de vida do achado** indefinido: o que acontece com um achado quando o dado-base muda ou a regra é reprocessada? Decisão humana é sobrescrita? → risco de duplicar achado ou apagar rótulo.
3. **Identidade/dedup do achado** não especificada → re-run gera achados duplicados.
4. **Dinheiro e data** sem padrão → bug clássico de float/timezone em sistema financeiro.
5. **Auth dos nossos usuários** (não do tenant-dado) mal especificada → RBAC, escopo por obra, SSO.
6. **Tempo real** prometido sem mecanismo (SSE? polling? websocket?).
7. **Raw landing vs canônico**: sem zona de pouso bruta, reprocessar exige re-puxar o Sienge.
8. **Resolução de config** (default→tenant→obra) e **snapshot de config no achado** para reprodutibilidade.
9. **Versionamento de dado** descrito como bitemporal — complexo demais para o MVP.
10. **Testes do conector sem credencial** e **golden tests das regras** (proteger o refactor do PoC).
11. **Concorrência de sync por tenant** (dois syncs simultâneos do mesmo tenant).
12. **Guardrails de custo/PII de LLM** concretos.
13. **Isolamento físico do benchmark** (schema vs database).

Os ADRs abaixo fecham cada um.

---

## ADR-01 — Eventos via Transactional Outbox + worker

**Decisão:** toda escrita no canônico que mude `content_hash` grava, **na mesma transação**, uma linha em `outbox_event(tenant_id, entity_type, entity_id, change_type, created_at, processed_at)`. Um worker consome o outbox e enfileira a reavaliação das regras cujas `applicable_entities()` incluem aquela entidade, no escopo afetado (obra/insumo/fornecedor).

**Por quê:** garante que nenhum evento se perde (mesma transação do dado); desacopla ingestão de avaliação; reprocessável (basta reprocessar o outbox).
**Trade-off:** uma tabela e um loop a mais — barato e padrão. Substitui o vago "evento dado mudou" de [arquitetura.md](./arquitetura.md) §3.

## ADR-02 — Ciclo de vida do achado (máquina de estados)

**Estados:**
`OPEN` → (humano) `ACCEPTED` | `DISMISSED` | `ESCALATED`; e por dado/reprocesso: `RESOLVED` (condição deixou de valer), `SUPERSEDED` (recalculado e substituído por novo achado de versão de regra/dado mais nova).

**Regras de transição no reprocesso:**
- Achado **ainda aberto** (`OPEN`) cuja condição **deixou de valer** após mudança de dado → `RESOLVED` (com motivo: "dado corrigido").
- Achado com **decisão humana** (`ACCEPTED`/`DISMISSED`/`ESCALATED`) é **sticky**: nunca é sobrescrito automaticamente. Reprocesso só anexa nota; não apaga rótulo (rótulo é ativo de ML — Camada 3).
- Recalcular com **nova versão de regra** gera novo achado e marca o antigo `SUPERSEDED`, preservando histórico.
- `value_ledger` é **imutável**; reversão (achado aceito que depois cai) entra como **true-up** (linha de estorno), nunca edição.

**Por quê:** protege o rótulo humano e o ledger de gainshare; evita duplicar/recriar achado a cada sync. Preenche o vazio de [modelo-dados.md](./modelo-dados.md) §7 e alinha com [gtm.md](./gtm.md) §8.

## ADR-03 — Identidade e dedup do achado

**Decisão:** cada regra define um `dedup_key` determinístico a partir do escopo (não do timestamp). Ex.:
- R1 sobrepreço: `hash(rule_id, order_item_id)`
- R2 cotação perdida: `hash(rule_id, order_id, item, melhor_cotacao_id)`
- R3 fracionamento: `hash(rule_id, creditor_id, categoria, janela_inicio)`
- R4 estouro: `hash(rule_id, project_id, catalog_item_id)`
- R5 divergência: `hash(rule_id, bill_id)`
- R6 sem concorrência: `hash(rule_id, order_id)`

`UNIQUE(tenant_id, dedup_key)`. Re-run faz **upsert** no achado (atualiza valor/severidade), não cria duplicado.
**Por quê:** idempotência do motor de regras, espelhando a idempotência da ingestão.

## ADR-04 — Padrão de dinheiro

**Decisão:** dinheiro em `NUMERIC(18,4)` no Postgres e `decimal.Decimal` no Python. **Proibido float** em qualquer caminho de valor. `currency` sempre junto do valor. Arredondamento `ROUND_HALF_UP`, 2 casas para apresentação em BRL. Um tipo `Money(amount: Decimal, currency: str)` central.
**Por quê:** evitar o bug financeiro clássico. Cross-cutting; vale para regras, ledger e R$ exposto.

## ADR-05 — Padrão de tempo

**Decisão:** armazenar `timestamptz` em **UTC**. Timezone de negócio = **America/Sao_Paulo**. Janelas de regra (ex.: fracionamento 30d) e "período" (mês) calculados na tz de negócio. Datas do Sienge normalizadas para UTC na ingestão; `valid_from/valid_to` em UTC.
**Por quê:** janelas e fechamentos mensais corretos; sem bug de fuso no fracionamento e no ledger.

## ADR-06 — Raw landing separado do canônico

**Decisão:** zona de pouso bruta append-only `raw_record(tenant_id, source, entity_type, source_external_id, payload jsonb, fetched_at, content_hash)`. A transformação para o canônico lê do raw. Reprocessar o canônico (ex.: corrigir um mapeamento) **não exige re-puxar o Sienge**.
**Por quê:** replayability, auditoria do que a fonte realmente entregou, e tolerância a bug de mapeamento. Refina o "staging raw" citado em [arquitetura.md](./arquitetura.md) §3.

## ADR-07 — Resolução de config + snapshot no achado

**Decisão:** `rule_config` resolve por precedência **default global → tenant → (futuro) obra**. Params tipados e validados (Pydantic). **No momento do achado, grava-se o snapshot da config efetiva e da referência usada** (`finding.config_snapshot`, `finding.reference_snapshot`).
**Por quê:** reprodutibilidade e explicabilidade ("este achado usou threshold 10% e SINAPI-PR-jun/2026") mesmo que a config mude depois. Reforça [regras.md](./regras.md) §5 e [ground-truth.md](./ground-truth.md).

## ADR-08 — Auth dos nossos usuários + RBAC + escopo

**Decisão (MVP):** usuários com e-mail + senha (hash **Argon2**), sessão via **JWT** (access curto + refresh) ou cookie httpOnly. Papéis: `owner`, `controller`, `procurement`, `viewer`, `tenant_admin`. Escopo: `membership(user_id, tenant_id, role, company_ids[], project_ids[])` — além do RLS por tenant, a app filtra por empresa/obra quando o papel for restrito. **SSO (OIDC/SAML)** fica para o enterprise (Fase 1), atrás da mesma interface de auth.
**Por quê:** [seguranca-lgpd.md](./seguranca-lgpd.md) §8 mencionava papéis mas não o mecanismo; multi-empresa/obra exige escopo acima do tenant.

## ADR-09 — Tempo real = SSE + push + polling de fallback

**Decisão:** o feed de achados usa **Server-Sent Events** (simples no FastAPI, unidirecional, suficiente) com **fallback a polling**. "Tempo real" = latência de minutos: sync incremental (~15 min) → outbox → regras → novo achado **empurra** evento SSE para o dashboard. Websocket só se precisar de bidirecional (não precisa no MVP).
**Por quê:** cumpre o requisito "online, tempo real" de [prd.md](./prd.md) §8 sem complexidade de websocket.

## ADR-10 — Concorrência de sync e rate limit por tenant

**Decisão:** **advisory lock** por `(tenant_id, source)` garante um sync por vez por tenant (sem sobreposição). Rate limiter **token bucket no Redis** por tenant para o Sienge. Jobs de sync são idempotentes (ADR-06 + chave natural).
**Por quê:** [conector-sienge.md](./conector-sienge.md) §5 falava de rate limit mas não de corrida entre syncs do mesmo tenant.

## ADR-11 — `SecretProvider` abstrato

**Decisão:** interface `SecretProvider.get(path)`; impl `EnvSecretProvider` (local, lê `.env`/ambiente) hoje; `VaultSecretProvider`/`FileSecretProvider` no servidor. **Toda** credencial (Sienge por tenant, `ANTHROPIC_API_KEY`, embeddings) passa pelo provider — nunca lida direto do ambiente no código de negócio.
**Por quê:** cumpre "segredos fora do repo" e a portabilidade local→servidor de [seguranca-lgpd.md](./seguranca-lgpd.md) §6.

## ADR-12 — Guardrails de custo e PII de LLM

**Decisão:** (a) **orçamento de tokens por tenant** no Redis, com teto que bloqueia chamada ao estourar; (b) **redação de PII** no prompt (remove CPF/nome pessoal quando não necessário à tarefa); (c) **roteamento de modelo** (Haiku para volume, modelo forte para Investigador/Narrador); (d) **cache de embeddings** por `hash(descrição normalizada)`.
**Por quê:** concretiza os guardrails de [agentes.md](./agentes.md) e o risco T4/de custo de [riscos.md](./riscos.md).

## ADR-13 — Testes de conector sem credencial (fixtures)

**Decisão:** gravar respostas reais do Sienge (sanitizadas, sem dado sensível) como **fixtures** e reproduzir no CI (estilo VCR). A lógica do conector (paginação, watermark, normalização, dead-letter) é testada **sem credencial viva**. Smoke ao vivo fica atrás de credencial (gated).
**Por quê:** destrava o desenvolvimento do conector antes de Q1/Q7 e protege contra regressão quando a API mudar.

## ADR-14 — Golden tests das regras

**Decisão:** para cada regra, fixtures determinísticos (cenário canônico) → achados esperados (severidade, **R$ exposto**, evidência). Rodam em CI.
**Por quê:** protege o **refactor do PoC** (Q2): garante que a lógica refatorada produz o mesmo resultado do motor original. Essencial para "incorporar e refatorar, não recomeçar".

## ADR-15 — Taxonomia de erros

**Decisão:** separar **erro de dado** (FK não resolve, campo faltante) → **dead-letter** por tenant, não derruba batch; de **erro transitório** (5xx/429/timeout) → retry com backoff/jitter + circuit breaker; de **erro de programação** → falha alta + alerta. Cada classe tem tratamento próprio.
**Por quê:** robustez operacional; concretiza [conector-sienge.md](./conector-sienge.md) §8 e [arquitetura.md](./arquitetura.md) §9.

## ADR-16 — Bootstrapping e privacidade do catálogo de insumos

**Decisão:** `catalog_item` é **semeado do SINAPI** (público) e **não contém dado de tenant**. O mapeamento descrição-do-cliente → catálogo é por tenant (`item_mapping`, com RLS). Embeddings: do nome canônico (catálogo) e **cache** dos embeddings das descrições cruas por `hash` (sem identificar tenant no vetor compartilhado). O catálogo cross-tenant é **referência pura** (sem preço, sem identidade).
**Por quê:** remove a ambiguidade de "catálogo compartilhado entre tenants" de [modelo-dados.md](./modelo-dados.md) §6 sem violar isolamento.

## ADR-17 — Isolamento físico do benchmark (Fase 1)

**Decisão:** o pool de benchmark fica em **database separado** (não só schema), com o **ETL de anonimização como único escritor** e **views read-only** para consumo. Decisão registrada agora; construção na Fase 1.
**Por quê:** endurece [seguranca-lgpd.md](./seguranca-lgpd.md) §5 (risco existencial D5/R4 em [riscos.md](./riscos.md)).

## ADR-18 — Observabilidade

**Decisão:** logs estruturados JSON (`structlog`) com `request_id`+`tenant_id` via contextvars; `/healthz` e `/readyz`; `/metrics` (Prometheus) com latência de sync, achados/dia, erro de conector, custo de LLM por tenant. Sem PII em log.
**Por quê:** concretiza [arquitetura.md](./arquitetura.md) §8.

## ADR-19 — Migrações, seed e deploy

**Decisão:** **Alembic** para schema; migração roda no entrypoint do container no deploy. **Seed sintético** (dados no formato Sienge) para dev/teste sem credencial. Backups via `pg_dump` agendado no servidor; restore drill documentado.
**Por quê:** operacionaliza o roadmap e destrava dev sem credencial (o PoC já tem dados sintéticos no schema do Sienge — vamos reaproveitar).

## ADR-20 — Versionamento de dado pragmático (não bitemporal)

**Decisão:** o canônico guarda a **linha corrente**; mudanças geram um snapshot em `entity_history(tenant_id, entity_type, entity_id, version, payload jsonb, content_hash, changed_at)` append-only. Abandono o bitemporal (`valid_from/valid_to` em todas as tabelas) do MVP — fica como opção futura.
**Por quê:** atende auditoria, reprocesso e "o pedido mudou depois de aprovado?" com **muito menos complexidade**. Simplifica [modelo-dados.md](./modelo-dados.md) §5/§9 para o MVP.

---

## Diagrama de fluxo revisado (com os ADRs)

```
Sienge API ──(rate-limit Redis, advisory-lock por tenant: ADR-10)──►
[Connector read-only] ──► raw_record (ADR-06)
        │ transform + normalize
        ▼
[Canônico] ──tx──► outbox_event (ADR-01) + entity_history (ADR-20)
        │
   [worker outbox] ──► enfileira reavaliação das regras afetadas
        ▼
[Motor de regras] ── dedup_key upsert (ADR-03) ── snapshot config+ref (ADR-07)
        │   Money NUMERIC/Decimal (ADR-04), tz negócio (ADR-05)
        ▼
[Finding + evidência] ── máquina de estados (ADR-02)
        │                         │
   [Triador]                 [SSE push: ADR-09] ──► Dashboard
        │                         │
        ▼                    revisão humana ──► rótulo (sticky) + value_ledger (imutável+true-up)
[Investigador/Narrador]          │
   (LLM: budget+PII guardrails ADR-12, secrets ADR-11)
```

## Reconciliação com os docs anteriores

- [README.md](./README.md): índice atualizado para incluir este doc e [plano-implementacao.md](./plano-implementacao.md).
- [modelo-dados.md](./modelo-dados.md): adicionar `raw_record`, `entity_history`, `outbox_event`, `membership`, `dedup_key`, `config_snapshot`/`reference_snapshot` no `finding`, e simplificar o versionamento (ADR-20). (Aplico no schema durante a construção.)
- [arquitetura.md](./arquitetura.md): o "evento dado mudou" agora é o outbox (ADR-01); tempo real é SSE (ADR-09).
- Demais docs permanecem válidos.
