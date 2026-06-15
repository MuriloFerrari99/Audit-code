# Arquitetura Agêntica (Hexagonal + CDM + OpenSquad)

> Decisão (2026-06-15): **evoluir o sistema Python existente** para esta
> arquitetura, em vez de re-plataformar para Node/Prisma. Reaproveita RLS
> endurecido, CI verde, billing e parsers. Os artefatos pedidos no prompt
> (schema, CDM, árvore, plano) estão materializados aqui no stack Python.

## Por que hexagonal
O motor de IA e o banco são **agnósticos a país e setor**. Tudo que varia
(formato de documento, fonte de preço, ERP, idioma) entra por **Adapters**
plugáveis atrás de **Ports**. Trocar BR→US ou construção→saúde = acoplar
adapters, sem tocar Core/CDM/banco.

## Camadas

```
backend/app/
├── canonical/              # CDM — interface universal do domínio
│   ├── document.py         #   CanonicalDocument, CanonicalItem, CanonicalParty,
│   │                       #   CanonicalRetentions, DocumentType, SourceFormat
│   └── mappers.py          #   formato bruto -> CDM (NF-e/NFS-e hoje; PDF US/EDI depois)
│
├── ports/                  # CONTRATOS (hexágono) — Core depende só disto
│   ├── parser.py           #   DocumentParser  (entrada: bytes -> CDM)
│   ├── reference.py        #   ReferencePriceProvider (saída: preço de mercado)
│   ├── erp.py              #   ErpActionPort   (saída: travar pagamento)
│   └── notification.py     #   NotificationPort(saída: e-mail de contestação)
│
├── connectors/             # ADAPTERS DE ENTRADA (driving)
│   ├── upload/             #   nfe.py, nfse.py, spreadsheet.py, load.py
│   └── sienge/             #   conector de ERP (read)
│
├── agents/                 # OPENSQUAD (orquestração do domínio)
│   └── squad/
│       ├── base.py         #   SquadContext, AgentResult, SquadAgent, log de raciocínio
│       ├── extractor.py    #   1) bytes -> CDM (usa adapters)
│       ├── enricher.py     #   2) anexa preço de referência (usa ReferencePriceProvider)
│       ├── auditor.py      #   3) roda regras determinísticas (rules/engine.run_all)
│       └── executor.py     #   4) abre Dispute (ERP/e-mail) — advisory -> ação
│
├── rules/                  # regras de negócio (preço, fiscal, pagamento, integridade, retenção)
├── billing/ admin/ ...     # contextos de aplicação já existentes
├── models/
│   ├── agentic.py          #   AgentReasoningLog (explicabilidade) + Dispute (mitigação)
│   ├── billing.py tenancy.py sourcing.py ...
│   └── ...
└── migrations/             # 0017_agentic: tabelas novas + tenant.industry/currency + RLS
```

## CDM — o contrato universal
`CanonicalDocument` (+`CanonicalItem`, `CanonicalParty`, `CanonicalRetentions`)
é imutável, em Decimal puro, serializável e auditável. **Todo** adapter de
entrada produz isto; Core e OpenSquad só conhecem o CDM. `tax_id` no lugar de
CNPJ, `country`/`currency` explícitos, `classification` (NCM/CFOP/HS) genérico.

## OpenSquad — pipeline orientado a eventos
Cada passo grava um `AgentReasoningLog` (run_id agrupa a execução; `agent_name`,
`status`, `confidence_score`, `reasoning_text`, `legal_citations`). O `SquadContext`
carrega `country/industry/locale` — é o que seleciona dinamicamente os adapters.

1. **Extrator** — fila de uploads → identifica formato → CDM (✅ NF-e/NFS-e).
2. **Enriquecedor** — itens do CDM → `ReferencePriceProvider` por país/setor.
3. **Auditor** — `rules/engine.run_all` (guardas anti-FP, confiança, calibração) → achados.
4. **Executor** — abre `Dispute`; com Port injetada, bloqueia pagamento no ERP
   ou envia contestação no idioma do tenant. Sem Port = `draft` (sem efeito).

## Multi-tenant / segurança (invariantes)
Tabelas novas (`agent_reasoning_log`, `dispute`) são tenant-scoped com **RLS**.
Ação externa do Executor é **deliberada, idempotente e auditada**. Nenhum segredo
no Git. `Tenant.country/industry/currency` guiam a seleção de adapters.

## Próximos passos (roadmap da Fase Agêntica)
- ✅ **P2 — Enriquecedor real:** `BrazilSinapiProvider` (Port) envolvendo
  `app/rules/references.py`, injetado no Enricher.
- ✅ **P3 — Orquestrador:** `SquadRunner.run_document` encadeia
  Extrator→Enriquecedor→Auditor com `run_id` único e dead-letter.
- ✅ **P4 — Executor com ação:** trava tripla — flag `tenant.auto_mitigation`
  (opt-in, default OFF), idempotência por achado, adapter **log-only seguro por
  padrão** (`erp_provider`/`notifier_provider`); `SiengeErpAdapter`/`SmtpNotifier`
  são skeletons gated. `POST /disputes` (restrito) + `GET /disputes`.
- ✅ **P5 — Citações legais:** `app/rules/citations.py` (IN RFB 971/2009 p/ INSS,
  LC 116/2003 p/ ISS); engine grava `finding.legal_citations` (migração 0019) e a
  API expõe no achado.
- ✅ **P6 — Multi-país:** `get_reference_provider(country, industry)` seleciona
  `BrazilSinapiProvider` (BR) ou `RSMeansProvider` (US, skeleton); o Runner usa o
  factory — acoplar país é só um adapter, Core/Enricher/Runner não mudam.
- ✅ **P7 — Event-driven + telas:** outbox `squad_audit` (upload publica) drenado
  por worker (`drain_audit_outbox`, tick 30s); `GET /agents/reasoning` + telas
  `/agents` (prontuário) e `/disputes` (mitigação).
- **Próximo (P8+):** ingerir base US (RSMeans) + adapter `us_pdf_invoice`; ligar
  `auto_mitigation` real com adapter de ERP homologado; go-live (deploy + Stripe).
