# Camada de ML

## Princípio

> ML **só onde supera regra fixa.** As regras determinísticas fazem o trabalho pesado e explicável. O ML entra onde uma regra fixa não dá conta: casar descrições ambíguas, aprender a banda de preço justa, achar padrões não codificados e prever preço. Todo output de ML que vira achado **passa por evidência + humano** (nada de caixa-preta).

## Os 4 jobs

| # | Job | Por que ML | Fase |
|---|-----|-----------|------|
| 1 | **Casamento / normalização de insumos** | descrições variam por empresa; regex não resolve | MVP (essencial) |
| 2 | **Benchmark de preço (banda aprendida)** | "% fixo" é cego a região/volume/spec | Fase 1 |
| 3 | **Anomalia não-supervisionada** | pega padrões que nenhuma regra codifica | Fase 1+ |
| 4 | **Previsão de preço de insumos-chave** | timing de compra (aço, cimento) | Fase 2 |

---

## Job 1 — Casamento / normalização de insumos · **pré-requisito do fosso**

**Problema:** "Aço CA-50 10mm" vs "Vergalhão 10.0" vs "VERG CA50 Ø10" são o mesmo insumo. Sem casar descrições para um **catálogo canônico**, não há comparação de preço entre obras nem entre empresas — e sem isso o benchmark (Camada 2) não existe.

**Abordagem (híbrida, em cascata):**
1. **Normalização determinística:** limpeza (uppercase, unidades, bitolas, sinônimos conhecidos) — barato, pega os casos óbvios.
2. **Embeddings (API externa):** embedding da descrição → busca por similaridade (`pgvector`) contra o catálogo canônico. Match acima de limiar alto = automático.
3. **LLM (agente Casador — ver [agentes.md](./agentes.md)):** casos ambíguos (similaridade média) → Claude desambigua com contexto (unidade, spec, faixa de preço) e propõe match + confiança.
4. **Humano no loop:** matches de baixa confiança vão para revisão; a decisão humana vira rótulo (Camada 3) e re-treina/calibra.

**Catálogo canônico:** **código SINAPI como espinha**; nós próprios para o que não existe no SINAPI. `catalog_item` é compartilhável entre tenants (é referência, não dado sensível); o **mapeamento** descrição-do-cliente → catálogo é por tenant (`item_mapping`).

**Dados necessários:** descrições de itens (orçamento, pedido, cotação) de todos os tenants + catálogo SINAPI + rótulos humanos.

**Baseline:** normalização + similaridade de embeddings com limiar; mede-se precisão/recall do match contra um set rotulado. LLM e feedback elevam a partir daí.

**Métrica:** % de itens auto-casados com alta confiança, precisão do match (amostra revisada), cobertura do catálogo.

---

## Job 2 — Benchmark de preço (banda aprendida) · **Fase 1**

**Problema:** "% fixo acima da mediana" é cego a região, período, volume, fornecedor e spec. Queremos prever o **preço esperado** de um insumo dado o contexto e flagrar desvio além de uma **banda aprendida**.

**Abordagem:**
- Modelo de regressão do preço esperado por `(catalog_item, região, período, faixa de quantidade, spec)`.
- Saída: preço esperado + intervalo (banda). Desvio fora da banda → sinal de sobrepreço (alimenta R1).
- **Cross-tenant anonimizado:** treina sobre `benchmark_price_observation` (schema separado, k-anonimato, sem `tenant_id` — ver [modelo-dados.md](./modelo-dados.md) §8 e [seguranca-lgpd.md](./seguranca-lgpd.md)).
- **Cold-start:** enquanto não há massa, R1 usa % fixo + mediana própria + SINAPI (ver [ground-truth.md](./ground-truth.md)).

**Dados necessários:** preços transacionados casados ao catálogo, com região/período/qty/spec; volume mínimo por célula (k-anonimato).

**Baseline:** mediana por `(insumo, região, período)` com banda por percentil (P10–P90). Modelo aprendido supera quando há dado suficiente.

**Métrica:** erro de previsão (MAE/MAPE) vs. baseline; precisão dos sobrepreços confirmados por humano.

---

## Job 3 — Anomalia não-supervisionada · **Fase 1+**

**Problema:** padrões suspeitos que nenhuma das 6 regras codifica (ex.: combinação atípica fornecedor/obra/horário/valor).

**Abordagem:** Isolation Forest / autoencoder sobre features de transação por tenant (e, com cuidado, no agregado). Saída = score de anomalia → entra na fila de triagem como "padrão atípico — investigar", sempre advisory, sempre com as features que explicam o score.

**Cuidado:** anomalia é o tipo mais propenso a falso-positivo e a "caixa-preta". Só promovemos a achado com explicação das features e com humano no loop. Começa como sinal interno de priorização antes de virar achado mostrado ao cliente.

**Baseline:** regras estatísticas simples (z-score por insumo/fornecedor) antes do modelo.

---

## Job 4 — Previsão de preço de insumos-chave · **Fase 2**

**Problema:** ajudar o timing de compra de commodities de obra (aço, cimento).

**Abordagem:** série temporal por insumo-chave (preço próprio + benchmark + indicadores públicos) → previsão de tendência. Entrega como **insight** ("janela favorável de compra"), não como achado de auditoria.

**Métrica:** acerto direcional da tendência; valor de timing capturado.

---

## Loop de feedback (o motor do fosso)

```
achado → revisão humana (aceitar/descartar/justificar) → rótulo (Camada 3)
   │
   ├─► re-treina casamento de insumo (Job 1) → catálogo melhor → benchmark melhor (Job 2)
   ├─► calibra thresholds por tenant (regras)
   └─► melhora ranking de anomalia (Job 3)
```

Cada cliente que entra e cada revisão que ocorre tornam o sistema mais certeiro — para aquele tenant e, via benchmark anonimizado, para todos. Esse é o ativo que compõe.

## Infra de ML (lean, online, tempo real)

- **Embeddings:** API externa (decisão do founder); cache em Postgres/Redis para não reembedar a mesma descrição.
- **Vetor:** `pgvector` no MVP (sem banco vetorial dedicado até o volume justificar).
- **Treino:** jobs batch no worker (RQ/Celery) — não bloqueia o caminho online.
- **Serving:** modelos leves carregados no serviço de ML; inferência online para casamento/banda.
- **Versionamento de modelo:** cada achado de origem ML grava a versão do modelo (reprodutibilidade), espelhando o versionamento de regra.
- **Governança de privacidade:** nenhum dado identificável de tenant alimenta modelo cross-tenant fora do pipeline anonimizado (ver [seguranca-lgpd.md](./seguranca-lgpd.md)).
