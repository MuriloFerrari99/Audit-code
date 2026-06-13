# Camada de Agentes (Claude)

## Princípios

1. **Read-only, sempre.** Agentes leem o modelo canônico e as referências; **não** têm nenhuma tool que escreva no ERP do cliente ou que tome ação com efeito colateral. Não existe ferramenta de escrita no toolset deles.
2. **Human-in-the-loop.** Agentes analisam e reportam; a decisão é humana. Especialmente na dimensão de integridade (contraparte).
3. **Explicabilidade.** Todo output de agente cita a evidência canônica (ids das entidades, valores, fonte de referência). Nada de afirmação sem lastro.
4. **Determinismo onde importa.** Cálculo de R$ e disparo de achado são do **motor de regras** (determinístico). O agente **monta narrativa, desambigua e prioriza** sobre o que a regra já produziu — não inventa achado nem recalcula valor por conta própria.
5. **Custo controlado.** Modelo certo para a tarefa: raciocínio pesado em modelo forte (Opus), alto volume/barato em Haiku. Cache e prompt enxuto.

## Roster

### Investigador
- **Tarefa:** dado um flag/achado, montar o **dossiê de evidência** puxando a cadeia `solicitação → cotação → pedido → nota → pagamento` do modelo canônico.
- **Input:** `finding` + acesso read-only ao canônico do tenant.
- **Output:** dossiê estruturado (linha do tempo da cadeia, valores, divergências, referência usada) + `finding_evidence` enriquecida e citável.
- **Modelo:** forte (raciocínio sobre cadeia e exceções).
- **Guardrail:** só lê entidades do `tenant_id` do achado (RLS + tenant fixado no contexto do agente).

### Casador de insumos
- **Tarefa:** resolver descrições ambíguas de insumo → `catalog_item` (ver [ml.md](./ml.md) Job 1) nos casos de similaridade média.
- **Input:** descrição crua + candidatos do `pgvector` + contexto (unidade, spec, faixa de preço).
- **Output:** match proposto + confiança + justificativa. Baixa confiança → fila humana.
- **Modelo:** Haiku/médio (alto volume).
- **Guardrail:** não cria `catalog_item` novo sem revisão; propõe.

### Triador
- **Tarefa:** priorizar a fila de achados por **materialidade × confiança × risco**, agrupar achados relacionados (mesmo fornecedor/obra), reduzir ruído.
- **Input:** achados abertos + R$ exposto + severidade + histórico de decisões do tenant.
- **Output:** fila ordenada + agrupamentos + razão da prioridade.
- **Modelo:** médio.
- **Guardrail:** não fecha nem descarta achado; só ordena/agrupa. Decisão é humana.

### Narrador
- **Tarefa:** gerar o **relatório mensal** e o **resumo executivo** na linguagem do dono (R$ exposto/validado/realizado, tendências, top achados, próximos passos).
- **Input:** achados do período + ledger de valor + tendências.
- **Output:** relatório (markdown/PDF) + resumo executivo curto.
- **Modelo:** forte (qualidade de escrita e síntese).
- **Guardrail:** todo número citado vem do dado/ledger; o agente não estima R$ — reporta o que o motor calculou.

## Orquestração

```
evento (achado novo / fim de período / item ambíguo)
        │
        ▼
  [Orquestrador]  ── decide qual agente, com qual contexto (tenant fixado)
        │
        ├─► Casador        (item ambíguo)         → match proposto
        ├─► Investigador   (achado relevante)     → dossiê
        ├─► Triador        (fila mudou)           → priorização
        └─► Narrador       (fechamento mensal)    → relatório
        │
        ▼
  resultados → dashboard / fila humana / alertas
```

- **Stateless por chamada**, contexto explícito (tenant, escopo). Sem estado global compartilhado entre tenants.
- **Idempotência:** reexecutar um agente sobre o mesmo achado não duplica efeito (resultados versionados).
- **Fila assíncrona:** chamadas de agente passam pelo worker (RQ/Celery), com retry e teto de custo.

## Guardrails (transversais)

| Guardrail | Como |
|-----------|------|
| **Sem escrita no ERP** | toolset dos agentes não inclui nenhuma ação de escrita externa; conector é read-only por design |
| **Isolamento de tenant** | contexto do agente fixa `tenant_id`; acesso a dado passa pela camada com RLS |
| **Sem PII desnecessária no prompt** | minimização — só o necessário para a tarefa entra no prompt |
| **Custo/orçamento** | teto de tokens por tarefa/tenant; modelo proporcional à tarefa; cache |
| **Explicabilidade** | output sempre referencia ids/valores/fonte; sem afirmação não-lastreada |
| **Advisory na dimensão 4** | linguagem "sinal a investigar", nunca "fraude confirmada"; humano decide |
| **Segredos** | chave de API via env/secret manager; verificada como ausente do ambiente/perfis (feito) |
| **Trilha** | toda execução de agente é logada no `audit_log` (quem/quando/sobre quê) |

## Onde o agente NÃO entra

- Não calcula R$ exposto (motor de regras faz).
- Não decide aceitar/descartar achado (humano faz).
- Não escreve no ERP nem dispara pagamento/ação.
- Não acessa dado de outro tenant.
- Não alimenta modelo cross-tenant com dado identificável.

## Custo e modelo

- **Regras determinísticas** carregam o grosso → LLM só onde agrega (dossiê, desambiguação, narrativa).
- **Seleção de modelo por tarefa:** forte para Investigador/Narrador; médio/Haiku para Casador/Triador de alto volume.
- **Telemetria de custo por tenant** para sustentar o gainshare e a margem da vaca leiteira.
