# Modelo Canônico de Dados

## 1. Princípios

1. **Canônico, não cópia.** Não espelhamos o Sienge campo a campo; mapeamos para entidades neutras de ERP/país/vertical. Trocar de ERP ou de país não muda o canônico — muda o connector.
2. **Multi-tenant em toda linha.** Toda tabela de dado de cliente tem `tenant_id NOT NULL` + RLS.
3. **Abstração país/vertical desde já.** `country_code`, `currency`, `vertical` presentes mesmo com um só valor hoje.
4. **Versionamento.** Mudanças de registro no ERP geram novas versões (não overwrite destrutivo) para rastrear "o que mudou e quando" — base da explicabilidade e do diff incremental.
5. **Separação identificável × agregado.** Dado do tenant vive em tabelas com RLS; o pool de benchmark vive em schema separado, só com agregado anonimizado.

## 2. Hierarquia de tenancy (confirmada)

```
tenant (grupo / incorporadora)        ← unidade de isolamento e cobrança
  └── company (empresa / CNPJ)        ← uma incorporadora tem N empresas
        └── project (empreendimento / obra)
              └── (transações: pedidos, notas, pagamentos, ...)
```

- **`tenant`** é a fronteira de RLS, billing, config e usuários.
- **`company`** carrega o CNPJ (chave para Receita/CEIS/integridade na Fase 1).
- **`project`** é a obra/empreendimento — granularidade de orçamento, R$ exposto e relatórios.

## 3. Estratégia de multi-tenancy

| Decisão | MVP | Enterprise (futuro) |
|---------|-----|---------------------|
| Isolamento | **RLS em schema compartilhado** | **schema-per-tenant** (migração) |
| Chave | `tenant_id` em toda tabela + policy RLS | schema dedicado por tenant |
| Conexão | role da app seta `SET app.tenant_id` por request | role/schema por tenant |
| Segredos do tenant | secret manager, namespaced por tenant | idem |

**Como o RLS funciona aqui:**
- A app usa um role Postgres **sem** `BYPASSRLS`.
- Cada request autenticado resolve o `tenant_id` e executa `SET LOCAL app.current_tenant = '<uuid>'` na transação.
- Toda tabela de dado de cliente tem policy: `USING (tenant_id = current_setting('app.current_tenant')::uuid)`.
- Jobs de background setam o tenant explicitamente por job.
- **Teste de isolamento** é critério de aceite: suíte que tenta ler/escrever cruzando tenant e deve falhar.

**Caminho para schema-per-tenant:** o código acessa tabelas por nome lógico; um resolver de schema (search_path por tenant) permite migrar clientes enterprise para schema dedicado sem mudar queries. Decisão adiada até o primeiro cliente exigir.

## 4. Entidades canônicas (a cadeia auditável)

Mapeamento campo a campo ao Sienge em [conector-sienge.md](./conector-sienge.md). Origem no Sienge em [fontes-dados.md](./fontes-dados.md).

```
budget_item (orçamento/insumo)
      │
quotation (cotação + negociação) ──┐
      │                            │
purchase_request (solicitação) ────┤
      │                            │
purchase_order (pedido + autorização)
      │
invoice / delivery (nota ↔ atendimento ao pedido)
      │
bill / payment (título / pagamento)

creditor (fornecedor)  ── referenciado por quotation, order, bill
catalog_item (insumo canônico) ── liga budget_item/order_item a SINAPI + benchmark
```

## 5. Campos comuns a toda entidade de dado de cliente

| Campo | Tipo | Nota |
|-------|------|------|
| `id` | uuid (PK) | id interno |
| `tenant_id` | uuid | RLS, NOT NULL |
| `company_id` | uuid | empresa/CNPJ |
| `project_id` | uuid (nullable) | obra, quando aplicável |
| `country_code` | char(2) | `BR` por ora |
| `currency` | char(3) | `BRL` por ora |
| `source` | text | `sienge` (futuro: `nfe`, `openfinance`...) |
| `source_external_id` | text | id no sistema de origem |
| `source_payload` | jsonb | payload bruto normalizado (auditoria/debug) |
| `content_hash` | text | hash do conteúdo (detecção de mudança) |
| `version` | int | versionamento |
| `valid_from` / `valid_to` | timestamptz | histórico temporal |
| `ingested_at` / `updated_at` | timestamptz | controle de sync |

**Chave natural / idempotência:** `UNIQUE (tenant_id, source, <entidade>, source_external_id, version)`.

## 6. Schemas (resumo por entidade)

> Esboço lógico; o DDL real (SQLAlchemy/Alembic) vem na implementação após o OK.

### `tenant`
`id, name, doc (CNPJ do grupo), country_code, plan, status, created_at`

### `company`
`id, tenant_id, name, cnpj, state (UF), city, created_at`

### `project` (empreendimento/obra)
`id, tenant_id, company_id, name, external_code, state (UF p/ SINAPI regional), status, budget_total, started_at`

### `creditor` (fornecedor)
`id, tenant_id, name, cnpj_cpf, type, contact, [fase1: integrity_status]`

### `catalog_item` (insumo canônico) — espinha do casamento e do benchmark
`id, canonical_name, vertical, sinapi_code (nullable), unit, spec_attributes (jsonb), embedding (vector), created_at`
> Compartilhável entre tenants (catálogo é referência, não dado sensível). O **mapeamento** descrição-do-cliente → catálogo é por tenant (ver `item_mapping`).

### `item_mapping`
`id, tenant_id, raw_description, catalog_item_id, confidence, source ('ml'|'human'), reviewed_by, created_at`

### `budget_item` (orçamento)
`+comuns, project_id, catalog_item_id, raw_description, unit, qty_budgeted, unit_price_budgeted, total_budgeted`

### `quotation` (cotação)
`+comuns, project_id, creditor_id, catalog_item_id, raw_description, qty, unit_price, valid_until, status, negotiation_round`

### `purchase_request` (solicitação) + `purchase_request_item`
`request: +comuns, project_id, requested_by, requested_at, status`
`item: request_id, catalog_item_id, raw_description, qty, unit`

### `purchase_order` (pedido) + `purchase_order_item` + `order_authorization`
`order: +comuns, project_id, creditor_id, request_id (nullable), total, status, ordered_at`
`item: order_id, catalog_item_id, raw_description, qty, unit_price, total`
`authorization: order_id, level, authorized_by, authorized_at, threshold_at_time` (histórico de alçada — chave p/ regra de fracionamento e sem concorrência)

### `invoice` / `delivery` (nota ↔ atendimento)
`+comuns, order_id, creditor_id, number, qty_delivered, unit_price_invoiced, total_invoiced, issued_at, [fase1: nfe_key, nfe_status]`

### `bill` / `payment` (título / pagamento)
`+comuns, order_id (nullable), creditor_id, amount, due_date, paid_at, status, [fase1: paid_account, openfinance_ref]`

## 7. Entidades de produto (não vêm do ERP)

### `finding` (achado)
`id, tenant_id, project_id, rule_id, severity, status (open|accepted|dismissed|escalated), exposed_amount_brl, reference_type (camada/fonte), reference_value, created_at, resolved_at`

### `finding_evidence`
`id, finding_id, entity_type, entity_id, role ('pedido'|'cotacao_mais_barata'|...), snippet (texto citável), value`
> Liga o achado às linhas canônicas exatas que o originaram → explicabilidade estrutural.

### `finding_review` (rótulo de ML)
`id, finding_id, tenant_id, decision (accept|dismiss|escalate), reason, reviewed_by, reviewed_at`

### `rule_config` (threshold por tenant)
`id, tenant_id, rule_id, params (jsonb), enabled, updated_by, updated_at`

### `value_ledger` (gainshare — ver gtm.md)
`id, tenant_id, project_id, finding_id, exposed_brl, validated_brl, realized_brl, period, status, evidence_ref`

### `audit_log` (trilha do próprio sistema)
`id, tenant_id, actor (user|system|agent), action, target_type, target_id, metadata (jsonb), at` — append-only.

## 8. Schema do benchmark (separado, anonimizado)

Schema **`benchmark`** físico-separado, **sem `tenant_id` identificável**:

### `benchmark_price_observation`
`id, catalog_item_id, region (UF/meso), period (mês), unit, price, qty_bucket, supplier_bucket (hash anonimizado), k_count`
- Só recebe observação quando a célula de agregação atinge **k-anonimato** (`[ASSUNÇÃO]` ≥3 tenants e ≥5 fornecedores distintos — ver [perguntas-abertas.md](./perguntas-abertas.md)).
- Origem identificável (qual tenant) **nunca** entra aqui. ETL de anonimização roda separado e só emite agregado. Detalhe em [seguranca-lgpd.md](./seguranca-lgpd.md).

## 9. Versionamento e migrações

- **DDL** versionado via Alembic; toda mudança de schema é migração revisável.
- **Dado:** versionamento temporal (`version`, `valid_from/to`) preserva o histórico — necessário para auditar "o pedido mudou depois de aprovado?" e para reprocessar regras retroativamente.
- **Contratos canônicos** versionados: se o significado de um campo canônico mudar, é uma nova versão de contrato (semver), e connectors declaram qual contrato atendem.
