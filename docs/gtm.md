# Go-to-Market e Metodologia de Gainshare

## 1. Motion de vendas: cunha SMB/mid → enterprise

| | SMB / mid (cunha) | Enterprise (escala) |
|--|-------------------|---------------------|
| Entrada | construtoras onde o founder tem deal flow; cliente zero = construtora do founder | grupos com multi-empresa/multi-empreendimento |
| Onboarding | **leve, baixo toque** (self-serve assistido): conectar Sienge, sync, primeiros achados em dias | guiado: SSO, revisão de segurança, múltiplos CNPJs/obras |
| Precificação | **mensalidade base + gainshare** (gainshare facilita o "sim") | base maior + gainshare + módulos (integridade, fiscal) |
| Requisitos técnicos | dashboard, e-mail, fila de revisão | SSO, trilha de auditoria, isolamento reforçado, SLAs, exportações |
| Venda | founder-led, ROI demonstrável rápido | ciclo mais longo, prova de valor + segurança |

A arquitetura serve os dois desde cedo (multi-tenant, RLS, config por tenant, onboarding leve + controles enterprise plugáveis — ver [arquitetura.md](./arquitetura.md) e [modelo-dados.md](./modelo-dados.md)).

## 2. Proposta de valor

"Auditamos 100% das suas compras continuamente e te mostramos, com evidência, **quanto você está deixando na mesa em R$** — e você só divide o ganho com a gente quando ele é real."

- ROI óbvio na construção (3–10% do custo de obra exposto a desperdício/sobrepreço).
- Risco baixo para o cliente (gainshare alinha incentivo).
- Diferencial: evidência citável + integridade de fornecedor (Fase 1) = "auditoria de gasto **+** integridade".

---

# Gainshare — Metodologia de Mensuração de Valor (nível Big4)

> Objetivo: uma metodologia **defensável, auditável e à prova de disputa** para medir o valor que a plataforma gera e sobre o qual se cobra. Desenhada no rigor que uma KPMG/Deloitte aplicaria a um contrato de *performance-based fee* / *shared savings*. Princípio-mãe: **conservadorismo e rastreabilidade** — na dúvida, contamos menos, e todo R$ cobrado tem trilha de evidência.

## 3. Definições (o funil de valor)

| Termo | Definição | Quem confirma |
|-------|-----------|---------------|
| **R$ Exposto (Gross Exposure)** | valor potencial bruto do achado, calculado pela regra de forma determinística | sistema |
| **R$ Validado (Validated)** | achado que o cliente **aceitou** como procedente | cliente (revisão) |
| **R$ Realizado (Realized)** | valor efetivamente **recuperado ou evitado**, confirmado por evidência no ciclo seguinte | cliente + evidência |
| **Base de Gainshare (Billable Savings)** | parcela do Realizado elegível à cobrança, após exclusões e regras anti-duplicidade | contrato |

**Faseamento contratual (decisão do founder, a→b):**
- **MVP (Fase a):** gainshare sobre **R$ Validado** (achados aceitos) — simples, vende rápido.
- **Maduro (Fase b):** gainshare sobre **R$ Realizado** (aceito **e** sanado, confirmado no ERP no ciclo seguinte) — mais defensável, mais alinhado a "valor real".

## 4. Os três baldes de economia (taxonomia Big4)

1. **Hard savings (recuperação):** dinheiro que volta ou que deixa de sair de um compromisso já firmado (ex.: pagamento duplicado estornado, nota corrigida antes do pagamento). Mais defensável.
2. **Cost avoidance (evitação):** sobrepreço/estouro evitado **antes** de virar caixa (ex.: pedido corrigido para o preço da cotação mais barata). Defensável com baseline claro.
3. **Process / governance savings:** valor de governança (ex.: fracionamento/sem concorrência corrigidos). **Não entram na base de gainshare por padrão** (difícil atribuir R$) — entram como valor de processo no relatório, não na fatura. Evita cobrança contestável.

> Regra: **só hard savings e cost avoidance, com baseline e evidência, compõem a base de gainshare.** Governança é valor demonstrado, não faturado (salvo acordo específico).

## 5. Baseline e contrafactual (o ponto mais sensível)

O valor exposto pela regra ≠ valor economizado. Precisamos do **contrafactual** ("o que teria acontecido sem a plataforma") com baseline explícito por regra:

| Regra | Baseline (o "teria sido") | Realizado (o "foi") | Economia |
|-------|---------------------------|---------------------|----------|
| Sobrepreço | preço que seria pago (referência) | preço efetivamente pago após correção | diferença × qty |
| Cotação perdida | preço do pedido original | preço da cotação mais barata, se renegociado | diferença |
| Divergência pgto | valor que seria pago a maior | valor corrigido | diferença |
| Estouro qty | consumo que seria faturado | consumo barrado/ajustado | diferença |
| Pagamento duplicado (F1) | 2ª via que sairia | estorno/bloqueio confirmado | valor da 2ª via |

**Regra de ouro do baseline:** o baseline é **documentado e congelado** no momento do achado (snapshot da referência usada — qual camada, qual valor — ver [ground-truth.md](./ground-truth.md)). Não se recalcula baseline depois para inflar economia.

## 6. Atribuição e janela

- **Atribuição:** só conta como nosso o valor cuja correção é **rastreável a um achado da plataforma** (o achado precede a correção e a correção bate com a recomendação). Achado gerado **depois** de a empresa já ter corrigido por conta própria → não conta.
- **Lookback / janela de realização:** a correção precisa ocorrer dentro de **N dias** do achado (`[ASSUNÇÃO]` 90 dias) para ser atribuída. Evita reivindicar mérito por coincidência tardia.
- **Run-rate (economia recorrente):** para sobrepreço de item recorrente, conta-se a economia **realizada no período**, não uma anualização especulativa, salvo cláusula de run-rate negociada e auditável.

## 7. Anti-gaming e anti-duplicidade

- **Sem dupla contagem:** um mesmo R$ não é contado por duas regras (ex.: sobrepreço + cotação perdida no mesmo item) — dedup por `(item, período)` escolhendo a regra de maior evidência.
- **Sem inflar exposto:** R$ exposto usa quantidade e preço reais do dado, não estimativa otimista.
- **Sem baseline móvel:** baseline congelado no achado.
- **Materialidade mínima:** achados abaixo de um piso de R$ (`[ASSUNÇÃO]`) não entram na fatura (ruído).
- **Reversões:** se uma correção é revertida depois (ex.: estorno cancelado), o Realizado é estornado no `value_ledger` (true-up).

## 8. Governança e disputa (o que dá confiança ao cliente)

- **`value_ledger` auditável:** cada R$ cobrado tem linha com `finding_id`, baseline congelado, evidência (`finding_evidence`), data de validação e de realização, status. (Ver [modelo-dados.md](./modelo-dados.md) §7.)
- **Gate de validação do cliente:** nada entra como Validado/Realizado sem o aceite do cliente no fluxo de revisão (rótulo Camada 3). O cliente sempre pode contestar um item.
- **Relatório de fechamento mensal** (agente Narrador): extrato do ledger, com cada item rastreável à evidência — o cliente "audita o auditor".
- **Processo de disputa:** item contestado sai da base até resolução; resolução documentada. Em enterprise, possibilidade de revisão independente do ledger.
- **True-up periódico:** ajuste retroativo de reversões/correções.

## 9. Estrutura de preço (referência; números a definir com o founder)

- **Mensalidade base:** cobre custo de servir (sync, infra, LLM) + margem mínima → preserva a vaca leiteira mesmo com gainshare baixo.
- **Gainshare:** **% sobre a Base de Gainshare** (Validado no MVP → Realizado maduro). Faixas possíveis: % único, ou escalonado (mais % nas primeiras economias, menos depois), ou com **cap** anual.
- **Cap/floor:** cap protege o cliente de uma fatura desproporcional num mês atípico; floor (mensalidade) protege nossa margem.
- `[ASSUNÇÃO]` percentuais, cap, piso de materialidade e janela exatos → definir com o founder (ver [perguntas-abertas.md](./perguntas-abertas.md)).

## 10. Por que isso é "Big4-grade"

- Taxonomia explícita de economia (hard / avoidance / process).
- Baseline contrafactual congelado e documentado por achado.
- Atribuição causal com janela e lookback.
- Anti-gaming e anti-dupla-contagem.
- Ledger auditável + gate de aceite do cliente + processo de disputa + true-up.
- Conservadorismo: governança não vira fatura; na dúvida, conta-se menos.

Isso transforma "confie que economizamos" em "**aqui está o extrato auditável de cada real que cobramos, rastreável à evidência e validado por você**".
