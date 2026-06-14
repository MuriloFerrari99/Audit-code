# Conector Sienge

> **Somente leitura.** Este conector nunca escreve no Sienge. Não há método de escrita no código.

## 1. Visão

O conector Sienge é a primeira implementação da interface `SourceConnector`. Responsabilidades: autenticar, puxar incrementalmente os endpoints da cadeia auditável, respeitar rate limit, fazer retry com backoff, garantir idempotência e normalizar para o modelo canônico ([modelo-dados.md](./modelo-dados.md)).

## 2. Autenticação

- **Mecanismo:** a API REST do Sienge usa **HTTP Basic Auth** por **subdomínio do cliente**.
  - Base URL: `https://api.sienge.com.br/{subdominio}/public/api/v1` (REST) e o serviço de **Bulk Data** em seu caminho próprio (`/bulk-data/v1/...`).
  - Credencial: **usuário de API + senha de API** gerados pelo cliente no Sienge (não são o login humano).
- **Armazenamento:** credenciais por tenant no **secret manager**, namespaced (`tenant/{id}/sienge/{user,password,subdomain}`). Nunca no repositório, nunca em log. (Ver [seguranca-lgpd.md](./seguranca-lgpd.md).)
- **Escopo mínimo:** solicitar ao cliente um usuário de API com permissão **somente de leitura** aos módulos necessários.

> `[ASSUNÇÃO — confirmar]` detalhes de escopo/permission do usuário de API e se o cliente zero usa REST + Bulk Data ou só um deles. Validaremos contra a base real no onboarding.

## 3. Mapa de endpoints → entidade canônica

| Entidade canônica | Endpoint Sienge | Tipo | Nota |
|-------------------|-----------------|------|------|
| `budget_item` (orçamento/insumo) | `/building-cost-estimations` (Engenharia > Custos Unitários) | REST | orçado por obra |
| `quotation` (cotação + negociação) | `/bulk-data/v1/purchase-quotations` | Bulk | volume alto → bulk |
| `purchase_request` (+itens) | `/purchase-requests/{id}` | REST | itens da solicitação |
| `purchase_order` (+autorização) | `/purchase-orders` | REST | inclui histórico de autorização/alçada |
| `invoice` / `delivery` | `/purchase-invoices/deliveries-attended` | REST | nota ↔ atendimento ao pedido |
| `bill` / `payment` | `/bills` (contas a pagar) | REST | título e pagamento |
| `creditor` (fornecedor) | `/creditors` | REST | fornecedor/credor |

## 4. Estratégia de sync incremental

**Objetivo:** atualização em tempo real (latência alvo: minutos) sem reprocessar tudo.

### 4.1 Watermark por entidade
- Para cada `(tenant, entidade)`, guardar um **watermark** (maior `updated_at`/data de modificação visto, ou cursor/offset do bulk).
- Pull incremental: buscar registros com data de modificação > watermark (onde o endpoint suportar filtro por data) ou paginar o bulk a partir do cursor.
- Endpoints **Bulk Data** (cotações): puxa em lote, paginado; ideal para carga inicial e janelas grandes.
- Endpoints **REST** (pedidos, notas, bills): puxa por filtro de data/intervalo + paginação.

### 4.2 Cadência
- **Carga inicial (backfill):** full pull histórico por tenant na entrada (janela configurável, ex.: 12–24 meses).
- **Incremental:** scheduler dispara por tenant em intervalo configurável (ex.: a cada 15 min). Entidades de alta mudança (pedidos, notas, bills) em cadência mais curta que entidades estáveis (orçamento).

### 4.3 Idempotência
- Chave natural: `(tenant_id, 'sienge', entidade, source_external_id)`.
- **Upsert** por chave + comparação de `content_hash`:
  - hash igual → no-op (não reescreve, não dispara regra).
  - hash diferente → nova `version`, dispara evento "mudou" → reavaliação de regras afetadas.
- Garante que reexecutar um sync não duplica nem gera achados fantasma.

## 5. Rate limiting, retry e robustez

- **Rate limiting:** client com limitador de taxa (token bucket) por tenant, parametrizado conservadoramente; respeita `429`/`Retry-After` se a API enviar.
- **Retry:** backoff exponencial com jitter para `429` e `5xx`; teto de tentativas; falha persistente → marca o job como degradado e alerta (não trava o tenant inteiro).
- **Timeouts** e **circuit breaker** por endpoint para isolar instabilidade do Sienge.
- **Paginação resiliente:** retoma da última página confirmada (cursor persistido), não reinicia do zero em falha.
- **Observabilidade:** métricas por tenant/endpoint (latência, taxa de erro, registros/min); log estruturado sem credenciais.

> Decisão operacional dos números exatos (limite de req/s, intervalo de sync, janela de backfill) fica comigo, calibrada contra a base real no onboarding — sem bloquear o founder.

## 6. Mapeamento campo a campo (a detalhar contra a API real)

> Esqueleto. Os nomes exatos de campo do Sienge serão confirmados contra a resposta real da API no onboarding do cliente zero e fixados aqui. O princípio: cada campo canônico declara sua origem.

### Exemplo — `purchase_order`
| Campo canônico | Origem provável (Sienge) | Transformação |
|----------------|--------------------------|---------------|
| `source_external_id` | id do pedido | direto |
| `project_id` | obra/empreendimento do pedido | resolve via `external_code` da obra |
| `creditor_id` | credor do pedido | resolve via `creditor.source_external_id` |
| `total` | valor do pedido | normaliza moeda/decimal |
| `ordered_at` | data do pedido | ISO 8601 / timezone |
| `status` | situação | mapa enum Sienge → enum canônico |
| `order_authorization[]` | histórico de autorização | extrai nível, autorizador, data, alçada vigente |

### Exemplo — `invoice` / `delivery`
| Campo canônico | Origem provável | Transformação |
|----------------|-----------------|---------------|
| `order_id` | pedido vinculado ao atendimento | resolve FK |
| `qty_delivered` | quantidade atendida | direto |
| `unit_price_invoiced` | preço da nota | normaliza |
| `total_invoiced` | total | normaliza |

> O mapeamento completo das 7 entidades vira tabela definitiva quando rodarmos o primeiro sync real. O que fica travado agora é a **estrutura** (quais campos canônicos cada entidade tem); o **binding** ao nome exato do Sienge é o passo de onboarding.

## 7. Interface `SourceConnector` (contrato para abstração)

Todo connector implementa:

```
class SourceConnector(Protocol):
    source_name: str            # "sienge"
    country_code: str           # "BR"
    def authenticate(tenant_secrets) -> Session
    def list_entities() -> list[EntityKind]
    def pull(entity, since_watermark, page) -> Iterator[RawRecord]
    def normalize(raw) -> CanonicalRecord   # → modelo canônico
    def health() -> ConnectorHealth
```

- Sienge é a primeira implementação. NF-e, Open Finance, CGU/Receita serão outras — **mesma interface**, garantindo que adicionar fonte/país = novo plugin, não rewrite (ver [latam-readiness.md](./latam-readiness.md)).

## 8b. Mapeamento real — validado contra a API da Alumbra (2026-06)

> Resultado da sondagem read-only contra `https://api.sienge.com.br/alumbra/public/api/v1`
> (auth Basic OK, HTTP 200). Substitui o esqueleto onde indicado.

**Comportamentos reais importantes (não estavam no esqueleto):**
- `bills` e `purchase-quotations` (bulk) **exigem `startDate`/`endDate`** — sync por janela de data.
- `purchase-invoices/deliveries-attended` é **dirigido por chave** (`purchaseOrderId` | `billId` | `sequentialNumber`), não lista livre.
- `purchase-requests` **não suporta GET de coleção** (405) — só por id/escrita. Para o MVP é dispensável (5/6 regras não dependem dele).
- `building-cost-estimations` (do brief) **não existe nesta API** (404). O orçamento/custos virá de outro recurso — `cost-databases` existe (catálogo de bases de custo). **Lacuna a resolver** (necessário só para R4 estouro de quantidade).
- Endpoint **bulk-data** confirmado: `…/public/api/bulk-data/v1/purchase-quotations`.

**Campos reais por entidade (chaves observadas):**

| Canônico | Endpoint | Campo real |
|----------|----------|-----------|
| `creditor.name` | `/creditors` | `name` (tradeName, cnpj, cpf, active) |
| `purchase_order.total` | `/purchase-orders` | `totalAmount` |
| `purchase_order.ordered_at` | idem | `date` (e `createdAt`/`modifiedAt`/`authorizedAt`) |
| `purchase_order.status` | idem | `status` (+`authorized`, `consistent`) |
| `purchase_order.creditor` | idem | `supplierId` |
| `purchase_order.project` | idem | `buildingId` |
| (autorização/alçada) | idem | `authorized`, `authorizedAt`; valor via `/purchase-orders/{id}/totalization` |
| `purchase_order_item.*` | `/purchase-orders/{id}/items` | `unitPrice`, `quantity`, `netPrice`, `resourceId`/`resourceCode`/`resourceDescription`, `unitOfMeasure`, `purchaseQuotations` (aninhado) |
| `bill.amount` | `/bills` (datas) | `totalInvoiceAmount` |
| `bill.creditor` | idem | `creditorId` (`debtorId`, `documentNumber`, `issueDate`, `installmentsNumber`, `status`) |
| `quotation.*` | bulk `/purchase-quotations` (datas) | `purchaseQuotationId`, `purchaseQuotationDate`, `purchaseQuotationItems`[], `purchaseQuotationSuppliers`[], `responseDeadline` |

**Watermark incremental:** usar `modifiedAt`/`lastModificationDate`/`lastModification` (existem nos payloads).

**Orçamento (R4) — ENCONTRADO:** `bulk-data/v1/building-cost-estimation-items` (5.288 itens p/ a obra 202). Campos: `buildingId`, `description`, `quantity` (orçada), **`measuredQuantity` (medida/executada)**, `unitPrice`, `totalPrice`, `unitOfMeasure`, `workItemId` (chave do serviço/insumo), `wbsCode`, `percentComplete`. → **R4 fica auto-contido**: `measuredQuantity` vs `quantity` (sem join com pedidos).

**Cotações (R2/R6) — estrutura mapeada:** `purchaseQuotationSuppliers[].negotiations[].negotiationItems[]` com `productId`, `unitPrice`, `quotedQuantity`, `negotiatedQuantity`, `selectedOption`; negotiation tem `sellersName`, `totalValue`. Contagem de fornecedores distintos = `len(purchaseQuotationSuppliers)` (R6); menor `unitPrice` por `productId` = melhor cotação (R2).
**Achado da sondagem:** o campo `purchaseQuotations` do item do pedido vem **vazio** nos pedidos amostrados (vários pedidos sem cotação registrada — já é sinal de R6). Logo o casamento R2/R6 deve ser por **`resourceId` (item do pedido) ↔ `productId` (item da cotação)** — confirmar que compartilham o mesmo namespace de "produto" rodando o pipeline com dado real (decisão de construção adiada para evitar lógica errada).

**Lacunas restantes:**
1. **`deliveries-attended`:** obter um pedido com entrega para fixar o shape (amostras vieram vazias) — R4 agora não depende disso.
2. **`purchase-requests`:** sem listagem (405); confirmar fora do MVP.
3. **`supply-contracts`:** existe (400 sem params) — relevante p/ dimensão 5 (contrato), Fase 2.

## 8. Tratamento de erros de dado

- **Registro inconsistente** (FK não resolve, campo obrigatório ausente): vai para uma **dead-letter** por tenant com motivo; não derruba o batch; é revisável.
- **Mudança de schema do Sienge:** detectada por validação Pydantic na normalização → alerta + dead-letter, não corrompe o canônico.
