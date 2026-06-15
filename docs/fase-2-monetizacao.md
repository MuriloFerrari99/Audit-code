# Fase 2 — Monetização (assinaturas, cobrança, painéis)

> Transforma o core de auditoria em **SaaS cobrável**. Alinhado à estratégia
> ([gtm.md](./gtm.md)): **mensalidade base + gainshare** (% sobre R$ Validado no
> MVP — só *hard savings* + *cost avoidance*; governança é valor demonstrado, não
> faturado). Multi-tenant rígido continua sendo invariante (RLS).

## Objetivos
1. **Planos & assinatura** por tenant, com limites de uso (ex.: documentos/mês).
2. **Medição de uso** (metering) para gating e upgrade por consumo.
3. **Extrato de gainshare** derivado do `value_ledger` (achados aceitos), com as
   regras anti-dupla-contagem do gtm.md.
4. **Cobrança recorrente** (mensalidade) + **fatura de gainshare** via provedor.
5. **Painel do cliente** (meu plano, uso, extrato, upgrade) e **painel admin**
   (tenants, planos, uso, gainshare, override).

## Modelo de dados (novo, tenant-scoped salvo onde indicado)
- `plan` — catálogo de planos (**global**, não tenant): `code`, `name`,
  `base_price`, `doc_limit_month`, `gainshare_pct`, `features` (JSON), `active`.
- `subscription` — assinatura do tenant: `plan_id`, `status`
  (trial/active/past_due/canceled), `period_start`, `period_end`,
  `provider`, `provider_ref` (id externo), `cancel_at_period_end`.
- `usage_counter` — uso por tenant/período: `period` (AAAA-MM), `docs_ingested`,
  `findings_emitted` (contadores incrementais; idempotentes).
- `billing_event` — linha de fatura: `period`, `kind` (base/gainshare),
  `amount`, `status` (draft/issued/paid/failed), `provider_ref`, `detail` (JSON).
  Base p/ auditoria da cobrança e conciliação com o provedor.
- Gainshare **não** vira tabela nova: é **calculado** do `value_ledger`
  (validated_amount dos achados aceitos, filtrando dimensão/tipo elegível) e
  materializado como `billing_event(kind=gainshare)` ao fechar o período.

## Metering (medição)
- Incrementa `usage_counter.docs_ingested` na carga (NF-e/NFS-e/linha de planilha)
  e `findings_emitted` no `run_all`. Idempotente por período.
- Gating: se `docs_ingested > plan.doc_limit_month` → bloqueia/ë avisa e sugere
  upgrade (no MVP: **avisa e deixa passar**, registra excedente; hard-block é opção).

## Gainshare (cálculo, regras do gtm.md)
- Base = Σ `value_ledger.validated_amount` de achados **aceitos** no período cujo
  `rule_id` seja elegível (sobrepreço/cotação/estouro/divergência = hard/cost
  avoidance). **Governança fora** (R3/R6 e afins não entram na fatura).
- Dedup por `(item, período)` já é responsabilidade do ledger/achado; aqui só
  somamos o que está validado. Sem anualização especulativa.
- `gainshare = base * plan.gainshare_pct`, com **cap** opcional do plano.

## Provedor de pagamento (DECISÃO DO FOUNDER — trava a fatia 3)
B2B brasileiro precisa de **PIX/boleto** (cartão sozinho não fecha). Opções:
- **Asaas/Iugu/Pagar.me (BR-nativo):** PIX + boleto + cartão recorrente, webhooks,
  fatura nacional. Melhor p/ construtora BR. (Recomendado p/ começar.)
- **Stripe (global):** ótimo p/ cartão e futuro LATAM/USD; PIX/boleto no BR é
  limitado. Melhor se a visão internacional for prioridade já.
- Arquitetura é **provedor-agnóstica**: um `BillingProvider` (adapter) isola o
  SDK; trocar/!adicionar provedor não toca o core. As fatias 1–2 **não dependem**
  da escolha.

## Rollout (incremental, verificável — planeje→constrói→valida→verde)
1. ✅ **Planos + assinatura + metering** (provedor-agnóstico, sem cobrança real):
   `plan`/`subscription`/`usage_counter`, contador ligado ao upload de notas,
   `GET /billing/me` + painel do cliente `/billing`. Plano **corporativo**
   (invoice_limit=3000, overage_price=1,90) seedado por `scripts.bootstrap_plans`.
   Fatura = base + max(0, notas − limite) × overage, calculada do uso real.
2. ✅ **Extrato de gainshare**: base = Σ `value_ledger.validated_amount` de
   achados aceitos de regras elegíveis (`R1,R2,R4,R5,F1,F3,P1,P2`; governança
   R3/R6, integridade e flags fiscais ficam fora). `GET /billing/statement`,
   `POST /billing/statement/close` (materializa `billing_event`, idempotente) e
   seção no painel do cliente.
3. ✅ **Provedor de pagamento** (adapter agnóstico + **Stripe**): `BillingProvider`
   isola o SDK; `POST /billing/checkout` cria a sessão recorrente; `POST
   /billing/webhook/stripe` verifica **assinatura** e atualiza o estado
   (active/past_due/canceled); botão "Ativar assinatura" no painel.
   *Configuração necessária (suas chaves):* `BILLING_PROVIDER=stripe`,
   `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`, e em cada `plan.features.stripe_price_id`
   o Price criado no painel da Stripe. Sem chaves, a cobrança fica desligada
   (provider=none) e o resto do sistema funciona normalmente.
4. ✅ **Painel admin** (plataforma, cross-tenant): `GET /admin/tenants` (plano,
   uso, fatura projetada), `GET /admin/plans`, `POST /admin/tenants/{id}/plan`
   (override). Gated por `is_superuser` (`require_platform_admin`); tela `/admin`
   só aparece p/ staff. **Upgrade por consumo**: `billing_summary.upgrade_suggested`
   recomenda o menor plano que comporta o uso quando estoura o limite; banner no
   painel do cliente. Promover staff: `python -m scripts.make_admin <email>`.

## Invariantes
RLS em tudo que é tenant-scoped; `plan` global é read-only para o tenant. Webhook
do provedor é **autenticado** (assinatura) e idempotente. Nenhum segredo no Git.
Cobrança sempre rastreável (`billing_event` + `audit_log`).
