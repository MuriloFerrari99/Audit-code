# Arquitetura

## 1. Princípios

1. **Read-only sobre o dado do cliente.** Conectores só leem. Nenhum caminho de escrita ao ERP existe no código.
2. **Conteinerizado e cloud-agnóstico.** Roda local (esta máquina) e em servidor próprio sem mudar código. Docker + Docker Compose hoje; pronto para Kubernetes se virar foguete.
3. **Modular por interface.** Conectores, pacotes de preço e regras são plugins atrás de contratos estáveis.
4. **Multi-tenant em cada camada.** `tenant_id` atravessa ingestão, storage, regras, agentes e UI.
5. **Explicabilidade carregada no dado.** O achado referencia as linhas canônicas que o originaram — evidência é estrutural, não gerada a posteriori.
6. **Tempo real por sync incremental + eventos.** Mudança ingerida → reavaliação de regras afetadas → achado disponível em minutos.

## 2. As 7 camadas

```
┌─────────────────────────────────────────────────────────────────────┐
│  (7) APLICAÇÃO   Dashboard Next.js · config tenant · fluxo de         │
│                  revisão · alertas (e-mail/WhatsApp) · SSO (ent.)     │
├─────────────────────────────────────────────────────────────────────┤
│  (6) AGENTES     Investigador · Casador de insumos · Triador ·        │
│      (Claude)    Narrador  — read-only, human-in-the-loop             │
├─────────────────────────────────────────────────────────────────────┤
│  (5) ML          Casamento de insumos · Benchmark de preço ·          │
│                  Anomalia não-supervisionada · Previsão de preço      │
├─────────────────────────────────────────────────────────────────────┤
│  (4) MOTOR DE    6 regras determinísticas · thresholds por tenant ·   │
│      REGRAS      evidência nativa · achados + R$ exposto              │
├─────────────────────────────────────────────────────────────────────┤
│  (3) MODELO      Entidades canônicas versionadas · Postgres + RLS ·   │
│      CANÔNICO    abstração país/vertical · separação ident./agregado  │
├─────────────────────────────────────────────────────────────────────┤
│  (2) REFERÊNCIA  Camada 0 (interno) · Camada 1 (SINAPI/CUB/PNCP/CGU) ·│
│                  Camada 2 (benchmark) · Camada 3 (feedback humano)    │
├─────────────────────────────────────────────────────────────────────┤
│  (1) INGESTÃO    SourceConnector: Sienge (MVP) · NF-e · Open Finance ·│
│                  CGU/Receita — auth, sync incremental, retry, idemp.  │
└─────────────────────────────────────────────────────────────────────┘
        TRANSVERSAIS: multi-tenancy/isolamento · segredos · trilha de
        auditoria do sistema · observabilidade · segurança · LGPD
```

## 3. Fluxo de dados (end-to-end)

```
  Sienge API (real)
        │  pull incremental (scheduler), Basic Auth por subdomínio
        ▼
  [Connector Sienge] ── normaliza ──► [Staging raw por tenant]
        │                                     │
        │                              dedup / idempotência (hash natural)
        ▼                                     ▼
  [Modelo canônico] ◄──── upsert versionado, tenant_id, country/vertical
        │
        │  evento "dado mudou" (entidade X do tenant T)
        ▼
  [Motor de regras] ── avalia regras afetadas ──► [Achados + evidência + R$]
        │                                                │
        │                                                ▼
        │                                      [Triador] prioriza por R$/sev.
        ▼                                                │
  [ML: casamento de insumo] ──► catálogo canônico ──► alimenta regra de preço
        │                                                │
        ▼                                                ▼
  [Benchmark cross-tenant] ◄── agregação anonimizada ── [Dashboard]
   (Camada 2, fase 1)                                    │
                                            revisão humana (aceitar/
                                            descartar/escalar)
                                                         │
                                                         ▼
                                            [Rótulos] ──► realimenta ML +
                                                          calibra thresholds
                                                         │
                                                         ▼
                                            [Narrador] ──► resumo executivo
                                                          + alertas
```

## 4. Componentes e responsabilidades

| Componente | Responsabilidade | Stack |
|------------|------------------|-------|
| **API / Backend** | Endpoints REST, autenticação, orquestração | Python + FastAPI |
| **Connectors** | Pull read-only por fonte, normalização | Python (pacote `connectors`) |
| **Scheduler / Workers** | Sync incremental, jobs de ML, retries | Worker assíncrono (ver §6) |
| **Rules engine** | Avaliação determinística das regras | Python (pacote `rules`) |
| **ML services** | Embeddings, casamento, benchmark, anomalia | Python (pacote `ml`) |
| **Agents** | Orquestração Claude (read-only) | Anthropic SDK |
| **DB** | Estado canônico + achados + rótulos + ledger | PostgreSQL + RLS |
| **Cache / fila** | Cache de embeddings, fila de jobs | Redis |
| **Object store** | Evidências grandes, exports, XMLs NF-e (fase 1) | S3-compatível (MinIO local) |
| **Frontend** | Dashboard, config, revisão | Next.js + TS (design via Claude Design) |

## 5. Decisões de stack e trade-offs

### 5.1 Linguagem e API — **Python + FastAPI**
- **Por quê:** o PoC já é Python; ML/embeddings/dados são nativos de Python; FastAPI é async, tipado (Pydantic) e gera OpenAPI. Mantém uma só linguagem do connector ao ML.
- **Alternativas:** Node/TS (unifica com frontend, mas perde o ecossistema de dados/ML e força reescrever o PoC). Go (performático, fraco em ML). **Veredito:** Python no backend de dado; TS só no frontend.

### 5.2 Banco — **PostgreSQL**
- **Por quê:** RLS nativo (isolamento multi-tenant barato e robusto), JSONB (evidência/payload flexível), extensões `pgvector` (embeddings) e particionamento (escala). Um banco resolve relacional + vetorial no MVP.
- **Alternativas:** banco vetorial dedicado (Pinecone/Qdrant) — adia para quando o volume de embeddings justificar; `pgvector` cobre o MVP. **Veredito:** Postgres + pgvector agora.

### 5.3 Scheduler / workers — **ver §6** (decisão deliberada para lean)

### 5.4 Agentes — **Anthropic SDK (Claude)**
- **Por quê:** orquestração agêntica read-only, forte em raciocínio sobre evidência e geração de relatório em linguagem natural. Modelos atuais: Opus para raciocínio pesado (Investigador/Triador), Haiku para tarefas baratas e de alto volume (pré-classificação).
- **Guardrails:** agentes não têm tool de escrita ao ERP; só leem o canônico. Detalhe em [agentes.md](./agentes.md).

### 5.5 Frontend — **Next.js + TypeScript**, design via **Claude Design**
- **Por quê:** SSR/streaming para "tempo real", ecossistema maduro, fácil de hospedar no mesmo servidor. O **design visual será produzido com Claude Design** na fase de implementação.
- **Alternativa de aceleração:** admin pronto (Retool) para o painel interno de operação nos primeiros dias — avaliar, mas o produto do cliente é Next.js.

### 5.6 Deploy — **Docker Compose local → servidor único → (opção) K8s**
- **Por quê:** o founder roda local agora e sobe para um servidor próprio depois. Compose dá paridade dev/prod barata. Cloud-agnóstico preserva a opção foguete sem custo hoje.

## 6. Scheduler e processamento assíncrono (decisão lean)

**Necessidade:** sync incremental periódico por tenant + jobs de ML + reavaliação de regras sob evento, tudo com retry/idempotência, rodando local hoje e em 1 servidor depois.

**Decisão:** **APScheduler** (agendamento) + fila/worker com **Redis + RQ** (ou Celery se a complexidade crescer) — tudo conteinerizado.
- **Por quê:** leve, sem dependência de cloud gerenciada, roda igual local e em servidor. RQ é mais simples que Celery e suficiente para o MVP; o contrato de "enfileirar job" é abstraído para trocar por Celery/SQS sem tocar a lógica.
- **Trade-off:** RQ não tem todas as features de Celery (workflows complexos), mas o MVP não precisa. Abstração de fila mantém a porta aberta.

**Idempotência:** cada registro ingerido tem uma **chave natural** (ex.: `tenant_id + source + entidade + id_externo`). Upsert por chave + hash de conteúdo evita duplicar e detecta mudança (dispara reavaliação só do que mudou).

## 7. Modos de execução

| Modo | Onde | Como |
|------|------|------|
| **Dev local** | esta máquina | `docker compose up` → API + Postgres + Redis + worker + frontend + MinIO |
| **Servidor único** | VPS/dedicado do founder | mesmo Compose + reverse proxy (Caddy/Traefik) + TLS + backups |
| **Foguete (futuro)** | cloud | Helm/K8s, Postgres gerenciado, object store gerenciado |

## 8. Observabilidade e operação

- **Logs estruturados** (JSON) com `tenant_id`, `trace_id`, nunca PII sensível em log.
- **Métricas:** latência de sync, achados/dia, taxa de erro de connector, custo de API de LLM por tenant.
- **Tracing** opcional (OpenTelemetry) — abstraído, ligado quando precisar.
- **Trilha de auditoria do próprio sistema:** quem leu o quê, qual sync rodou, qual achado foi gerado/revisado — imutável (append-only). Ver [seguranca-lgpd.md](./seguranca-lgpd.md).

## 9. Riscos arquiteturais (resumo; detalhe em riscos.md)

- **Acoplamento ao Sienge:** mitigado pela interface `SourceConnector`.
- **Custo de LLM por volume:** mitigado por cache de embeddings, uso de Haiku onde cabe, e regras determinísticas fazendo o trabalho pesado (LLM só onde supera regra fixa).
- **Vazamento cross-tenant:** mitigado por RLS + testes de isolamento + separação física do pool de benchmark.
