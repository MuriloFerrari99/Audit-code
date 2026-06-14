# Frontend — Auditoria de Gastos

Next.js (App Router) + TypeScript + Tailwind. Consome a API do backend.

## Rodar local
```
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                  # http://localhost:3000
```
Ou via `docker compose up` na raiz (sobe junto com a API).

## Login (dados do seed)
- e-mail: `founder@cliente.com`
- senha: `audit12345`

(Rode `make seed` no backend antes.)

## Telas
- `/login` — autenticação
- `/` — visão geral (R$ exposto/validado, resumo executivo do Narrador, prioridades)
- `/findings` — fila de achados com filtros (status, regra)
- `/findings/[id]` — dossiê de evidência + análise + fluxo de revisão (aceitar/descartar/escalar)

## Design system
`components/ui.tsx` + tokens em `tailwind.config.ts`. Estruturado para sincronizar
com o **Claude Design** via o skill `/design-sync` (DesignSync) quando desejado.
