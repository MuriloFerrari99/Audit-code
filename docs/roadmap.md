# Roadmap com Gates

> O roadmap mapeia a decisão **vaca → foguete**. Cada fase tem critério de pronto e cada transição é um **gate objetivo** (ver [estrategia.md](./estrategia.md) §5). Não se avança por entusiasmo; avança-se por evidência.

## Fase 0 — MVP vaca leiteira

**Objetivo:** provar que achamos R$ real no dado real do cliente zero (construtora do founder).

**Escopo:**
- Conector Sienge (read-only, base real, sync incremental, idempotência).
- Modelo canônico multi-tenant (RLS) com abstração país/vertical.
- As **6 regras** do PoC, refatoradas e incorporadas.
- Referências Camada 0 (interno) + Camada 1 (SINAPI/CUB).
- Casamento de insumo mínimo (normalização + embeddings + fila humana) — o suficiente para a regra de preço.
- Dashboard mínimo: fila priorizada, dossiê de evidência, R$, tendência; fluxo aceitar/descartar/escalar (gera rótulo).
- Resumo executivo mensal (Narrador).
- Alertas por e-mail.
- `value_ledger` (gainshare: exposto → validado).
- Transversais: isolamento testado, segredos fora do repo, `audit_log`, observabilidade básica.

**Critérios de pronto (DoD):**
- [ ] 7 entidades da cadeia ingeridas do Sienge real de ≥1 tenant.
- [ ] 6 regras gerando achados com evidência + R$.
- [ ] Teste de isolamento multi-tenant passando.
- [ ] Dashboard com fluxo de revisão funcional e rótulos persistidos.
- [ ] Resumo executivo mensal gerado.
- [ ] Ledger registrando exposto/validado.
- [ ] Nenhum segredo no repo.

**Gate G1 (saída):** **R$ real achado e validado** pelo cliente zero **+** os primeiros clientes pagantes fechados.

---

## Fase 1 — Auditoria completa (Brasil / construção)

**Objetivo:** das 6 regras (dimensão preço + auto-consistência) para a auditoria completa universal.

**Escopo:**
- **Dimensão fiscal (NF-e):** ingestão de XML do cliente + validação SEFAZ; nota fria, divergência pedido↔nota, imposto/crédito.
- **Dimensão integridade (CEIS/CNEP/CEPIM/Receita):** checagem de contraparte (advisory forte).
- **Dimensão pagamento (Open Finance):** pagamento duplicado, sem lastro, conta divergente.
- **Casamento de insumo (ML maduro)** + início do **benchmark (Camada 2)** com k-anonimato.
- WhatsApp (Business API) além de e-mail.
- Controles enterprise iniciais (SSO, trilha reforçada).
- Gainshare evolui para **Realizado** (aceito e sanado).

**Critérios de pronto:**
- [ ] As 4 dimensões universais operando (preço, fiscal, pagamento, integridade).
- [ ] Benchmark gerando referência para ≥X insumos com k-anonimato.
- [ ] Casamento de insumo com precisão alvo.
- [ ] Cofre de certificados NF-e funcional.

**Gate G2 (saída):** **repetibilidade** — o produto entrega valor em construtoras além do cliente zero, com onboarding previsível.

---

## Fase 2 — Horizontal Brasil

**Objetivo:** sair da construção para novos verticais, reusando o núcleo universal.

**Escopo:**
- Novos **pacotes de preço plugáveis** por vertical (saúde: Banco de Preços/CMED; agro: CEPEA/CONAB; frota: FIPE/ANP/ANTT; cross-setor: Painel de Preços/PNCP).
- Dimensão 5 (**contrato/conformidade**) configurável por cliente.
- Onboarding self-serve mais maduro (cunha SMB em escala).
- Conectores de outras fontes além do Sienge, conforme demanda.

**Critérios de pronto:**
- [ ] ≥1 vertical novo onboarda em < X semanas usando só configuração de pacote (sem rewrite).
- [ ] Dimensão de contrato/conformidade ativa para ≥1 cliente.

**Gate G3 (saída):** **tração + decisão de capital** + 1 cliente LATAM identificado.

---

## Fase 3 — Foguete / LATAM

**Objetivo:** expandir para LATAM, México primeiro (CFDI).

**Escopo:**
- Ativar a abstração de país (ver [latam-readiness.md](./latam-readiness.md)): conector de ERP local, pacote de preço local, feed de sanções local, parser fiscal CFDI.
- Billing multi-moeda/multi-país, localização de UI.
- Infra escalável (K8s, Postgres gerenciado), multi-região se necessário.
- Compliance de dados local (ex.: LFPDPPP MX).

**Critérios de pronto:**
- [ ] 1 cliente LATAM operando com conector + pacote + feed locais.
- [ ] Núcleo universal reusado sem rewrite (só plugins novos).

---

## Linha do tempo (relativa, sem datas fixas)

```
G0 ──► [Fase 0: MVP] ──G1──► [Fase 1: auditoria completa BR] ──G2──►
[Fase 2: horizontal BR] ──G3──► [Fase 3: foguete/LATAM]
```

Cada gate é uma **decisão consciente** de alocar capital/esforço, não uma passagem automática. A vaca leiteira pode, legitimamente, parar na Fase 1 ou 2 e ser um ótimo negócio — o foguete é opção, não destino obrigatório.

## Próximo passo após este pacote

1. Sua aprovação dos docs.
2. Proposta de **estrutura de pastas do repositório** + **plano de implementação do MVP** (já esboçada na mensagem de entrega — aguarda seu OK).
3. Você me entrega o **motor Python do PoC** → incorporo e refatoro (não recomeço).
