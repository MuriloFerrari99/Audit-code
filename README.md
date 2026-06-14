# Auditoria de Gastos & Integridade (Spend Intelligence)

Plataforma multi-tenant que lê o ERP da empresa (**Sienge** primeiro), **somente leitura**,
audita 100% das compras continuamente e devolve achados com **evidência + R$**, em 4 dimensões:
**Preço · Fiscal · Pagamento · Integridade do fornecedor**. Advisory — o humano decide.

> Posicionamento: auditoria **gerencial** de gastos. **Não** é auditoria independente (termo regulado).

## Como rodar
Ver **[DEPLOY.md](./DEPLOY.md)**. Resumo (macOS):
```bash
bash scripts/install_runtime.sh && cp .env.example .env
make up && make migrate && make seed && make test
# App http://localhost:3000  ·  API http://localhost:8000/docs
```

## O que o sistema faz
- **Regras determinísticas** por dimensão (R1–R6 preço, F1–F3 fiscal, P1–P2 pagamento, I1–I5 integridade),
  cada achado com **evidência citável**, **R$ exposto** e **score de confiança**.
- **Higiene de dados**: o que checar/corrigir no Sienge (reduz ruído na origem).
- **Aprendizado por empresa**: aceitar/descartar calibra a confiança das regras por tenant.
- **Onboarding self-serve** + agente; conexão Sienge validada ao vivo.

## Arquitetura
- Backend Python/FastAPI + Postgres (RLS, role `app_rw` sem superusuário) + Redis + worker.
- Frontend Next.js/TS (design no Claude Design).
- Conectores read-only por fonte (Sienge); ML só onde supera regra fixa.
- Documentação completa em **[docs/](./docs/README.md)** (arquitetura, dados, regras, segurança/LGPD,
  ML, agentes, módulos, **[auditoria de código](./docs/auditoria-codigo-2026-06-14.md)** e
  **[checklist de go-live](./docs/go-live.md)**).

## Estado
Núcleo das 4 dimensões + UX + endurecimento (CI, isolamento por RLS provado em teste,
dead-letter, build reproduzível). Pendências de go-live e features gated por credencial:
ver **[docs/go-live.md](./docs/go-live.md)**.

## Princípios inegociáveis
Somente leitura no ERP · isolamento multi-tenant absoluto · explicabilidade (evidência sempre) ·
nunca falhar em silêncio · segredos fora do repo · LGPD.
