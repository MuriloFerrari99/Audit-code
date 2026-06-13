# Riscos e Mitigações

Severidade: 🔴 alta · 🟠 média · 🟢 baixa-controlada. Cada risco tem dono implícito (founder/eng) e mitigação de design.

## 1. Riscos técnicos

| # | Risco | Sev | Mitigação |
|---|-------|-----|-----------|
| T1 | **Acoplamento ao Sienge** (mudança de API/schema quebra ingestão) | 🟠 | Interface `SourceConnector`; validação Pydantic na normalização; dead-letter + alerta em mudança de schema; canônico não corrompe |
| T2 | **Casamento de insumo impreciso** (mata a comparação e o benchmark) | 🔴 | Cascata determinística→embeddings→LLM→humano; rótulos re-treinam; só auto-casa em alta confiança; SINAPI como espinha |
| T3 | **Falso-positivo erodindo confiança** | 🔴 | Thresholds por tenant; calibração por feedback (Camada 3); Triador prioriza; advisory + evidência sempre |
| T4 | **Custo de LLM/embeddings escalando** | 🟠 | Regras determinísticas fazem o grosso; Haiku onde cabe; cache de embeddings; teto de custo por tenant; telemetria |
| T5 | **Vazamento cross-tenant** | 🔴 | RLS + teste de isolamento como DoD; benchmark em schema separado sem `tenant_id`; pipeline de anonimização dedicado |
| T6 | **Tempo real sob carga** (sync + regras + ML) | 🟠 | Sync incremental por watermark; reavaliação só do que mudou; fila assíncrona; particionamento futuro |
| T7 | **Rate limit / instabilidade do Sienge** | 🟠 | Token bucket, backoff+jitter, circuit breaker, retomada por cursor; degrada o tenant sem derrubar os outros |
| T8 | **Lock-in de infra impede o foguete** | 🟢 | Conteinerizado, cloud-agnóstico; abstrações de fila/secret/storage |

## 2. Riscos de dado

| # | Risco | Sev | Mitigação |
|---|-------|-----|-----------|
| D1 | **Qualidade do dado do ERP** (campos vazios, FK quebrada) | 🟠 | Dead-letter por tenant; não derruba batch; revisável; regras tolerantes a dado faltante (não geram achado fantasma) |
| D2 | **SINAPI como referência teórica** (não reflete preço real) | 🟠 | Cascata de referência; benchmark (Camada 2) substitui quando maduro; severidade ajustada pela qualidade da referência |
| D3 | **Massa insuficiente para o benchmark (cold-start)** | 🟠 | Camada 0/1 cobrem o MVP; k-anonimato evita benchmark prematuro; % fixo até haver dado |
| D4 | **Baseline de gainshare contestável** | 🔴 | Baseline congelado no achado; ledger auditável; só hard/avoidance faturam; governança não fatura (ver [gtm.md](./gtm.md)) |
| D5 | **Reidentificação no benchmark** | 🔴 | k-anonimato; supressão de células pequenas/outliers; fornecedor como hash; revisão anti-reverse |

## 3. Riscos regulatórios e jurídicos

| # | Risco | Sev | Mitigação |
|---|-------|-----|-----------|
| R1 | **Confusão com "auditoria independente" (CVM/CFC)** | 🔴 | Terminologia firme: *spend intelligence* / auditoria interna gerencial; nunca "auditoria independente"; contrato e marketing alinhados |
| R2 | **LGPD — base legal / tratamento indevido** | 🔴 | Operador sob contrato; DPA + ROPA; base legal documentada; minimização; retenção; DPO (ver [seguranca-lgpd.md](./seguranca-lgpd.md)) |
| R3 | **Dimensão integridade acusa fornecedor injustamente** | 🔴 | Advisory forte ("sinal a investigar"); fonte oficial citada; humano decide; nunca rótulo automático de fraude |
| R4 | **Uso de dado do cliente para benchmark sem autorização** | 🔴 | Autorização contratual; opt-out; só agregado anonimizado; nunca preço identificável cruzando clientes |
| R5 | **Acesso indevido / incidente de segurança** | 🟠 | Menor privilégio, MFA, criptografia, trilha imutável, plano de resposta a incidente |

## 4. Riscos de negócio

| # | Risco | Sev | Mitigação |
|---|-------|-----|-----------|
| N1 | **Dependência do cliente zero** (concentração) | 🟠 | Cliente zero valida e gera referência; G1 exige clientes pagantes além dele |
| N2 | **Gainshare difícil de cobrar / disputado** | 🔴 | Metodologia Big4: ledger, baseline congelado, gate de aceite, disputa, true-up; mensalidade base protege margem |
| N3 | **Onboarding pesado mata a cunha SMB** | 🟠 | Onboarding leve (conectar Sienge → achados em dias); controles enterprise plugáveis, não obrigatórios no SMB |
| N4 | **Ciclo enterprise longo trava caixa** | 🟢 | Vaca leiteira sustenta via SMB/gainshare enquanto enterprise amadurece |
| N5 | **Fosso lento para compor** (poucos clientes no início) | 🟠 | Valor já existe sem o fosso (Camada 0/1); fosso é upside, não pré-requisito de venda |
| N6 | **Founder-led não escala** | 🟢 | Documentar processo; produto reduz toque; só vira problema na escala (problema bom de ter) |
| N7 | **Expansão prematura (foguete antes da hora)** | 🟠 | Gates objetivos; anti-escopo explícito; "construa para o agora" |

## 5. Top 5 a vigiar (resumo)

1. **T2/T3 — casamento + falso-positivo:** confiança do cliente depende disso. É o coração técnico.
2. **T5/D5/R4 — isolamento e anonimização:** uma falha aqui é existencial (confiança + jurídico).
3. **N2/D4 — gainshare defensável:** o modelo de receita só funciona se for incontestável.
4. **R1/R3 — posicionamento e advisory:** evitar problema regulatório e reputacional.
5. **T1/T7 — robustez do conector Sienge:** é a porta de entrada de todo o valor.
