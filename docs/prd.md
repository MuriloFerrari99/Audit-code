# PRD — Plataforma de Auditoria Contínua de Gastos e Integridade

## 1. Visão de produto

Uma camada de inteligência sobre o gasto da empresa. Conecta-se (somente leitura) às fontes de dado que a empresa já usa, audita 100% das transações de compra continuamente e entrega achados acionáveis — cada um com **severidade, referência, evidência citável, pedido(s) envolvidos e valor exposto em R$** — para que um humano decida.

**Não é** ERP, não escreve no ERP, não toma ação com efeito colateral, não é auditoria contábil independente. É *spend intelligence*: advisory, explicável, com humano no loop.

## 2. Usuários e personas

| Persona | Papel | Job principal | O que vê |
|---------|-------|---------------|----------|
| **Dono / Diretor** | Decisor econômico, paga a conta | "Quanto estou perdendo e está melhorando?" | Resumo executivo mensal, R$ exposto/recuperado, tendência |
| **Controladoria / Financeiro** | Operador primário | "Onde focar minha revisão limitada?" | Fila de achados priorizada, evidência, fluxo aceitar/descartar/escalar |
| **Suprimentos / Compras** | Auditado e parte interessada | "Esse achado procede? Como respondo?" | Achado individual, dossiê de evidência, justificativa |
| **Admin do tenant** (enterprise) | TI/segurança do cliente | "Quem acessa o quê, com que credencial?" | Config, usuários, SSO, trilha de auditoria, conexões |

Persona primária do MVP: **Controladoria** (operador) + **Dono** (consumidor do resumo).

## 3. Jobs-to-be-done

1. *Quando* fecho um período de compras, *quero* saber onde paguei caro / errado / sem governança, *para* recuperar dinheiro e corrigir o processo.
2. *Quando* recebo um achado, *quero* a evidência completa da cadeia (solicitação → cotação → pedido → nota → pagamento), *para* julgar em segundos sem caçar dado no ERP.
3. *Quando* tenho equipe pequena, *quero* a fila priorizada por materialidade, *para* gastar minha atenção limitada no que mais importa em R$.
4. *Quando* apresento ao dono, *quero* um resumo executivo na linguagem dele, *para* mostrar o valor que a ferramenta gera.
5. *Quando* vou comprar de um fornecedor, *quero* saber se ele é idôneo (sanções, situação cadastral, conflito), *para* evitar risco de integridade. *(Fase 1)*

## 4. Modelo de auditoria: 5 dimensões

Detalhe das fontes em [fontes-dados.md](./fontes-dados.md). Resumo:

| # | Dimensão | Pergunta | Tipo | Fase |
|---|----------|----------|------|------|
| 1 | **Preço** | "Está caro?" | Vertical / plugável | MVP (interno + SINAPI) |
| 2 | **Documento fiscal** | "A nota é válida e bate com o pedido?" | Universal | Fase 1 |
| 3 | **Pagamento** | "Pagou certo, uma vez, na conta certa?" | Universal | Fase 1 |
| 4 | **Contraparte / integridade** | "Eu deveria comprar dessa empresa?" | Universal | Fase 1 |
| 5 | **Contrato / conformidade** | "Respeitou contrato, orçamento, política?" | Por cliente | Fase 2 |

## 5. Escopo do MVP (Fase 0)

**Dentro:**
- Conector Sienge (somente leitura, sync incremental, base real).
- Modelo canônico multi-tenant com abstração país/vertical.
- As **6 regras** do PoC (refatoradas): sobrepreço, cotação perdida, fracionamento, estouro de quantidade, divergência pedido→pagamento, sem concorrência. (Ver [regras.md](./regras.md).)
- Referências Camada 0 (auto-consistência) e Camada 1 (SINAPI/CUB). (Ver [ground-truth.md](./ground-truth.md).)
- Dashboard mínimo: fila de achados, dossiê de evidência, R$, tendência; fluxo aceitar/descartar/escalar (gera rótulo de ML).
- Resumo executivo mensal (agente Narrador).
- Alertas por e-mail. *(WhatsApp → Fase 1.)*
- Gainshare operacional (ledger de valor — ver [gtm.md](./gtm.md)).

**Fora do MVP** (ver anti-escopo em [estrategia.md](./estrategia.md) §4).

## 6. Métrica de valor

A métrica-mãe é **R$ exposto detectado → R$ validado → R$ realizado** (funil de valor):

1. **R$ exposto:** soma do valor dos achados gerados (potencial bruto). Cálculo determinístico por regra.
2. **R$ validado:** achados que o cliente **aceitou** como procedentes (gera rótulo positivo).
3. **R$ realizado:** valor efetivamente recuperado/evitado, confirmado no ciclo seguinte. **Base do gainshare maduro.**

Métricas secundárias: precisão dos achados (aceitos / total), tempo médio de revisão por achado, cobertura (% de pedidos auditados — meta 100%), taxa de reincidência por fornecedor/obra.

> A metodologia completa de mensuração (baseline, atribuição, anti-gaming, governança) está em [gtm.md](./gtm.md) §Gainshare — desenhada no rigor de uma Big4.

## 7. Princípios de produto (não-negociáveis)

1. **Read-only.** Nunca escreve no ERP nem dispara ação com efeito colateral.
2. **Explicabilidade nativa.** Todo achado cita sua evidência e a referência usada. Nada de caixa-preta.
3. **Advisory, não veredito.** O sistema aponta desvio; o humano julga. Cuidado redobrado na dimensão 4 (integridade do fornecedor) — uma acusação infundada de fraude tem custo reputacional alto.
4. **Isolamento absoluto.** Dado de um cliente nunca vaza para outro; benchmark só com agregado anonimizado.
5. **Humano no loop = motor de aprendizado.** Cada decisão (aceitar/descartar/justificar) calibra thresholds e treina o ML.

## 8. Requisitos não-funcionais

- **Atualização em tempo real:** software online; achados aparecem conforme o sync incremental traz dado novo (latência alvo: minutos, não dias).
- **Disponibilidade:** alvo 99% no MVP (1 servidor) → 99.9% no caminho enterprise.
- **Portabilidade:** roda local nesta máquina e em servidor próprio sem mudança de código (conteinerizado).
- **Auditabilidade do próprio sistema:** todo acesso e toda geração de achado são logados (trilha imutável).
- **Performance:** sync incremental de um tenant médio (dezenas de obras) em minutos; reavaliação de regras incremental.

## 9. Critérios de aceite do MVP

- [ ] Conector Sienge puxa as 7 entidades da cadeia de dado real de ≥1 tenant.
- [ ] As 6 regras rodam sobre o dado canônico e geram achados com evidência + R$.
- [ ] Dashboard exibe fila priorizada, dossiê e fluxo de revisão.
- [ ] Decisões de revisão são persistidas como rótulos.
- [ ] Resumo executivo mensal gerado.
- [ ] Isolamento multi-tenant verificado por teste (tenant A não lê dado de B).
- [ ] Nenhum segredo no repositório; credenciais via env/secret manager.
- [ ] Ledger de gainshare registra R$ exposto/validado/realizado.
