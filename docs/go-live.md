# Checklist de Go-Live

> Portão de produção da auditoria ([auditoria-codigo-2026-06-14.md](./auditoria-codigo-2026-06-14.md) §8).
> Marcar PRONTO só com TUDO verde. Estado em 2026-06-14.

## Portão (bloqueia cliente pagante)

| # | Requisito | Estado | O que falta |
|---|-----------|:------:|-------------|
| 1 | Zero achados CRÍTICOS | 🟡 | C-1 corrigido (código); **provar no CI**. C-3 = rotacionar credencial |
| 2 | Isolamento multi-tenant **provado por teste** | 🟡 | teste existe (`test_isolation` sob `app_rw`); **rodar o CI** para evidência verde |
| 3 | Nenhum segredo no repo/histórico | 🟢 | confirmado limpo; `.env` gitignored; gitleaks no CI |
| 4 | Suíte existe, passa e cobre caminhos críticos | 🟡 | existe + CI configurado; **executar** (precisa do repo no GitHub) |
| 5 | Read-only no ERP garantido | 🟢 | por design (só GET); sem método de escrita |

## Ações para fechar (em ordem)

1. **Subir o repositório no GitHub** → o CI roda e gera a evidência (testes verdes, incl. isolamento). Fecha #1/#2/#4.
2. **Rotacionar a credencial de API do Sienge** (foi exposta no chat) — C-3.
3. **Revisar DPA/contrato + base legal LGPD** antes do 1º cliente pagante.
4. **Backups** do Postgres configurados + restore testado.
5. **TLS** no reverse proxy do servidor.

## Já endurecido (feito)
- C-1 RLS: runtime usa `app_rw` (sem superusuário) — RLS aplicado de fato.
- A-2: worker de auditoria contínua (APScheduler).
- A-3: `dead_letter` — ingestão nunca falha em silêncio.
- A-4: `requirements.lock` (backend) + `package-lock.json` (frontend) — build reproduzível.
- M-1: CI com lint + types + suíte (Postgres real) + scanners.
- Qualidade dos achados: higiene de dados + filtros por natureza + score de confiança + calibração por tenant.

## Features gated (não bloqueiam go-live; ligam com credencial)
- **I1** fornecedor sancionado → chave gratuita do Portal da Transparência.
- **F6** nota fria/SEFAZ → certificado digital A1/A3 do cliente.
- **Open Finance** (conta divergente/conciliação) → agregador (Pluggy/Belvo) + consentimento bancário.

## Posicionamento (não esquecer)
- "Auditoria **gerencial** de gastos" (spend intelligence), **advisory**, humano decide.
- Nunca "auditoria independente" (termo regulado CVM/CFC).
