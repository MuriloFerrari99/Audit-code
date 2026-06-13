# Pacote de Planejamento — Plataforma de Auditoria Contínua de Gastos e Integridade

> **Status:** Fase de planejamento (pré-código de aplicação).
> **Posicionamento:** *Spend intelligence* / auditoria interna e gerencial de gastos. **Não** é auditoria independente no sentido contábil/CVM/CFC.
> **Regra de ouro de arquitetura:** *arquitete para a opção (vaca → foguete), construa para o agora (Brasil, lean, lucrativo).*

Este diretório é a fonte de verdade do planejamento. Todo documento é versionado em Git e revisado antes de virar código.

## Índice

| # | Documento | O que responde |
|---|-----------|----------------|
| 1 | [estrategia.md](./estrategia.md) | Vaca → foguete, gates de decisão, o que abstrair vs. construir agora |
| 2 | [prd.md](./prd.md) | Produto, usuários, jobs-to-be-done, métrica de valor, escopo do MVP |
| 3 | [arquitetura.md](./arquitetura.md) | As 7 camadas, fluxo de dados, decisões e trade-offs |
| 4 | [modelo-dados.md](./modelo-dados.md) | Entidades canônicas, schemas, multi-tenancy, abstração país/vertical |
| 5 | [conector-sienge.md](./conector-sienge.md) | Endpoints, auth, sync incremental, mapeamento campo a campo |
| 6 | [fontes-dados.md](./fontes-dados.md) | As 5 dimensões e suas fontes (dia-1 vs. depois, universal vs. vertical) |
| 7 | [ground-truth.md](./ground-truth.md) | As 4 camadas de "verdade" / referência |
| 8 | [regras.md](./regras.md) | As 6 regras do MVP + framework para adicionar novas + thresholds por tenant |
| 9 | [ml.md](./ml.md) | Os 4 jobs de ML, dados, baseline, loop de feedback |
| 10 | [agentes.md](./agentes.md) | Roster de agentes Claude, orquestração, guardrails, human-in-the-loop |
| 11 | [gtm.md](./gtm.md) | Cunha SMB → enterprise, **metodologia de gainshare nível Big4** |
| 12 | [seguranca-lgpd.md](./seguranca-lgpd.md) | Isolamento, segredos, base legal, retenção, anonimização do benchmark |
| 13 | [latam-readiness.md](./latam-readiness.md) | O que abstrair agora p/ não refazer depois (sem construir multi-país) |
| 14 | [roadmap.md](./roadmap.md) | Fases 0–3 com gates de decisão e critérios de pronto |
| 15 | [riscos.md](./riscos.md) | Riscos técnicos, de dado, regulatórios e de negócio + mitigação |
| 16 | [perguntas-abertas.md](./perguntas-abertas.md) | Decisões pendentes e assunções a confirmar |
| 17 | [revisao-arquitetura.md](./revisao-arquitetura.md) | Revisão crítica pré-construção: 20 ADRs que fecham os buracos do "como" |
| 18 | [plano-implementacao.md](./plano-implementacao.md) | WBS granular: épicos, tarefas, dependências, DoD, bloqueios |

## Decisões já travadas (input do founder)

1. **Base real do Sienge desde o dia 1** (API, Basic Auth por subdomínio).
2. **Hierarquia de tenant:** grupo/incorporadora = tenant → empresas (CNPJ) → empreendimentos/obras.
3. **Isolamento:** RLS em schema compartilhado no MVP; caminho para schema-per-tenant no enterprise.
4. **Embeddings via API externa**; produto **online com atualização em tempo real**.
5. **Deploy:** desenvolvimento local nesta máquina → depois servidor próprio. **Conteinerizado e cloud-agnóstico.**
6. **Gainshare nível Big4** (ver [gtm.md](./gtm.md)).
7. **Frontend desenhado com Claude Design.**
8. **LGPD:** estrutura proposta do zero (ver [seguranca-lgpd.md](./seguranca-lgpd.md)).

## Como ler

- Para entender **o porquê**: `estrategia.md` → `prd.md`.
- Para entender **o como**: `arquitetura.md` → `modelo-dados.md` → `conector-sienge.md`.
- Para entender **o valor**: `regras.md` → `ground-truth.md` → `gtm.md`.
- Para entender **o futuro**: `ml.md` → `latam-readiness.md` → `roadmap.md`.
