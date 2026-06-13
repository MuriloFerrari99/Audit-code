# Motor de Regras

## 1. Princípios

1. **Determinístico.** Dado o mesmo input e config, a mesma saída. Auditável e testável.
2. **Explicabilidade nativa.** Toda regra emite `finding_evidence` ligando às linhas canônicas exatas + a referência usada (qual camada — ver [ground-truth.md](./ground-truth.md)).
3. **Thresholds por tenant.** Parâmetros em `rule_config` (jsonb), default global + override por tenant; calibrados pelo feedback humano (Camada 3).
4. **R$ exposto sempre.** Toda regra calcula o valor em R$ exposto, com fórmula declarada.
5. **Incremental.** Mudança em entidade dispara reavaliação só das regras afetadas (não full scan).
6. **ML só onde supera regra fixa.** A regra é o trabalho pesado; o ML entra na referência (banda de preço) e no casamento de insumo, não substitui a regra.

## 2. Contrato de uma regra

```
class Rule(Protocol):
    id: str
    severity_default: Severity
    dimension: int                      # 1..5 (ver fontes-dados.md)
    def applicable_entities() -> list   # o que dispara reavaliação
    def evaluate(ctx: TenantContext, scope) -> list[Finding]
    # cada Finding carrega: severity, exposed_amount_brl, evidence[], reference
```

Adicionar regra = nova classe que implementa o contrato + entrada no registry + config default. Sem tocar o core.

## 3. As 6 regras do MVP

> Lógica reaproveitada do PoC em Python (será **refatorada e incorporada**, não reescrita do zero). Os parâmetros abaixo são defaults — todos overridáveis por tenant.

### R1 — Sobrepreço
- **Pergunta:** o preço pago/cotado está acima da referência?
- **Referência (cascata):** benchmark (Cam.2, futuro) → SINAPI regional (Cam.1) → mediana histórica do tenant (Cam.0).
- **Disparo:** `purchase_order_item`, `invoice`.
- **Lógica:** compara `unit_price` do item contra a referência do `catalog_item` na UF/período. Flag se desvio > banda.
- **Threshold default (`[ASSUNÇÃO]` cold-start):** desvio > **10%** acima da referência (configurável); evolui para **banda aprendida** quando o benchmark amadurecer.
- **R$ exposto:** `(unit_price - referência) × qty`.
- **Evidência:** item do pedido, valor de referência, fonte/camada, período/UF.

### R2 — Cotação perdida
- **Pergunta:** comprou acima de uma cotação válida mais barata que existia?
- **Referência:** Camada 0 (as próprias cotações).
- **Disparo:** `purchase_order` vs. `quotation`.
- **Lógica:** para o insumo/fornecedor/janela, existe cotação **válida** (dentro da validade, mesma spec) com `unit_price` menor que o do pedido?
- **R$ exposto:** `(preço_pago - melhor_cotação) × qty`.
- **Evidência:** pedido + cotação mais barata (citável: fornecedor, data, validade, preço).

### R3 — Fracionamento
- **Pergunta:** vários pedidos do mesmo fornecedor/insumo logo abaixo da alçada, em janela curta (driblando a alçada de aprovação)?
- **Referência:** Camada 0 (alçada vigente em `order_authorization` + janela).
- **Disparo:** `purchase_order` + `order_authorization`.
- **Lógica:** agrupa pedidos por `(creditor, catalog_item|categoria, janela)`; flag se N pedidos, cada um logo abaixo do `threshold_at_time`, somam acima da alçada.
- **Thresholds default (`[ASSUNÇÃO]`):** janela = **30 dias**; "logo abaixo" = dentro de **10%** abaixo da alçada; N ≥ **2**.
- **R$ exposto:** soma dos pedidos que deveriam ter exigido alçada superior (valor sob governança burlada).
- **Evidência:** lista dos pedidos, alçada vigente, soma na janela.

### R4 — Estouro de quantidade
- **Pergunta:** quantidade atendida acima da orçada por obra/insumo?
- **Referência:** Camada 0 (`budget_item.qty_budgeted`).
- **Disparo:** `delivery`/`invoice` agregado por `(project, catalog_item)`.
- **Lógica:** soma atendida > qty orçada × (1 + tolerância).
- **Threshold default (`[ASSUNÇÃO]`):** tolerância **5%**.
- **R$ exposto:** `(qty_atendida - qty_orçada) × unit_price`.
- **Evidência:** orçamento da obra, somatório de atendimentos.

### R5 — Divergência pedido → pagamento
- **Pergunta:** pagou acima do valor do pedido?
- **Referência:** Camada 0 (`purchase_order.total`).
- **Disparo:** `bill`/`payment` vinculado a `order`.
- **Lógica:** valor pago > valor do pedido × (1 + tolerância).
- **Threshold default (`[ASSUNÇÃO]`):** tolerância **0–2%** (margem para arredondamento/frete configurável).
- **R$ exposto:** `valor_pago - valor_pedido`.
- **Evidência:** pedido, nota, pagamento (a cadeia).

### R6 — Sem concorrência
- **Pergunta:** pedido relevante fechado com fornecedor único, sem concorrência (governança)?
- **Referência:** Camada 0 (relevância por valor + ausência de cotações concorrentes).
- **Disparo:** `purchase_order` relevante vs. `quotation`.
- **Lógica:** pedido acima de valor de relevância com **0/1** cotação concorrente registrada.
- **Threshold default (`[ASSUNÇÃO]`):** relevância = valor > limite configurável por tenant; mínimo de cotações esperado configurável.
- **R$ exposto:** marcado como **valor sob governança** (não necessariamente perda direta) — severidade de processo, não de R$ perdido.
- **Evidência:** pedido, contagem de cotações, valor.

## 4. Severidade e priorização

- **Severidade** = f(dimensão de risco, magnitude do desvio, materialidade em R$, confiança da referência).
- O **Triador** (agente — ver [agentes.md](./agentes.md)) ordena a fila por **materialidade × confiança**, para a equipe gastar atenção no que rende.
- Achados de **integridade (dimensão 4, Fase 1)** recebem tratamento "advisory forte": severidade alta mas linguagem de "sinal a investigar", nunca acusação.

## 5. Thresholds por tenant

- `rule_config(tenant_id, rule_id, params jsonb, enabled)`.
- Resolução: default global → override por tenant → (futuro) override por obra.
- **Calibração automática (Camada 3):** se um tenant descarta sistematicamente uma faixa de achado, sugerimos ajuste de threshold (com aprovação humana — não muda sozinho silenciosamente).

## 6. Como adicionar uma regra nova

1. Implementar a classe `Rule` (id, dimensão, entidades de disparo, `evaluate`).
2. Declarar a **cascata de referência** (de qual camada tira a verdade).
3. Definir **fórmula de R$ exposto** e **evidência** emitida.
4. Registrar defaults em `rule_config`.
5. Testes: unitário (lógica), de explicabilidade (evidência presente e citável), de isolamento (respeita tenant).
6. Versionar: regra tem versão; achados gravam a versão da regra que os gerou (reprodutibilidade).

## 7. Reprocessamento

- Regras são versionadas; mudar uma regra/threshold permite **reprocessar histórico** (o dado é versionado temporalmente — ver [modelo-dados.md](./modelo-dados.md) §9) para mostrar "o que teria sido pego".
- Reprocessar **não** apaga rótulos humanos: achados revisados mantêm seu histórico de decisão.
