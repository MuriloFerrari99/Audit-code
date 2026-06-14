# Auditoria de Código — 2026-06-14

> Auditor externo, cético e independente. Premissa: há falhas sérias até prova em contrário.
> Ferramentas rodadas neste ambiente (macOS, **Python 3.9** — o projeto exige 3.11; **sem Docker, sem Postgres**), o que por si limita a verificação e **é um achado**.

---

# PARTE A — Resumo executivo (linguagem de negócio)

## Veredito: 🔴 VERMELHO

**Dá para colocar na frente de um cliente pagante hoje? NÃO.**

O sistema está **bem desenhado e já lê dado real** (conexão com o Sienge da Alumbra validada), mas tem **falhas existenciais não resolvidas e não testadas**. O mais grave: na configuração entregue, **o isolamento entre clientes provavelmente não está funcionando** — e isso nunca foi provado por execução, porque a suíte de testes **nunca rodou** (falta ambiente). Para um sistema que promete "o dado de um cliente jamais vaza para outro", isso é eliminatório.

## Top 5 riscos por impacto de NEGÓCIO

1. **Vazamento entre clientes (isolamento furado).** O app conecta no banco como **superusuário**, e superusuário do Postgres **ignora a trava de isolamento (RLS)**. Tradução: hoje, o dado do cliente A pode ser lido na sessão do cliente B. **Impacto: fim da empresa + processo de LGPD.** *(CRÍTICO)*
2. **Isolamento nunca foi provado.** Existe um teste que verificaria isso, mas ele **nunca foi executado** (sem banco no ambiente). "Confiar que isola" não é isolar. **Impacto: você não sabe se está seguro.** *(CRÍTICO)*
3. **Credencial real de cliente exposta.** A senha de API do Sienge da Alumbra foi **colada no chat** e está em arquivo local. Não vazou para o repositório (bom), mas precisa ser **rotacionada imediatamente**. **Impacto: acesso indevido ao ERP da Alumbra.** *(CRÍTICO)*
4. **Achados podem ser falsos (sem medir erro).** As regras usam limites "chutados" (ex.: alçada de R$ 50 mil fixa, que não é a da Alumbra) e o casamento de cotações tem **lacuna conhecida** que pode marcar "sem concorrência" indevidamente. Não há **nenhuma métrica de taxa de falso-positivo**. **Impacto: mostrar acusação errada a um cliente destrói a confiança.** *(ALTO)*
5. **A auditoria contínua não está, de fato, ligada.** O "trabalhador" que deveria sincronizar e auditar sozinho é um **esqueleto** (só dorme). Hoje só roda no manual. **Impacto: o produto "audita 100% continuamente" não cumpre a promessa — e pode deixar de auditar sem ninguém perceber.** *(ALTO)*

## Notas por esfera (0–10)

| # | Esfera | Nota | Por quê (resumo) |
|---|--------|:----:|------------------|
| 1 | Correção e lógica | 4 | Regras existem e os mapeadores foram testados contra payload real; mas limites chutados e R2/R6 com risco de falso-positivo |
| 2 | Testes | 2 | Suíte existe mas **nunca rodou**; sem cobertura; isolamento não provado |
| 3 | Segurança | 3 | bandit limpo (médio/alto), sem segredo no repo; mas **RLS furado** e credencial exposta |
| 4 | Privacidade/isolamento (LGPD) | 2 | Isolamento provavelmente **inativo** e não testado; anonimização do benchmark não construída |
| 5 | Confiabilidade/erro | 3 | Retry/backoff existem; mas **falha silenciosa** no ingest e worker não roda |
| 6 | Arquitetura/manutenção | 7 | Estrutura limpa, ADRs, docs fortes — ponto genuinamente bom |
| 7 | Desempenho/escala | 4 | N+1 no carregamento de itens; custo de LLM contido; sem teste de carga |
| 8 | Dados/ML/agentes | 3 | Evidência rastreável (bom); mas **sem métrica de precisão** e superfície de prompt injection |
| 9 | Observabilidade | 3 | structlog + /metrics existem; sem alerta, sem dead-letter, audit_log não ligado a tudo |
| 10 | Dependências/supply chain | 3 | Vulnerabilidades em npm (alta) e pip (7); **sem lockfile** |
| 11 | Deploy/config/DevOps | 3 | Separação .env boa; mas bug de config do RLS, **sem CI**, segredo só protegido por .gitignore |
| 12 | Conformidade do produto | 7 | Explicabilidade estrutural, advisory, terminologia correta nos docs |

**Média ≈ 3,6 / 10.**

## Ações priorizadas (ordem de impacto)

1. **Criar um role de aplicação sem superusuário e sem BYPASSRLS** e fazer o app conectar com ele. *(corrige o #1)*
2. **Rodar a suíte de testes contra um Postgres real** e exigir que o teste de isolamento passe **antes de qualquer cliente**. *(prova o #2)*
3. **Rotacionar a senha de API do Sienge** da Alumbra agora. *(corrige o #3)*
4. Implementar **dead-letter + alerta** no ingest (nunca auditar pela metade em silêncio) e **ligar o worker/scheduler**. *(#5, falha silenciosa)*
5. Definir **métrica de falso-positivo** e calibrar limites por tenant (começar pela alçada real da Alumbra); validar o casamento `resourceId↔productId`. *(#4)*
6. Adicionar **lockfile** (pip + npm) e atualizar dependências vulneráveis; montar **CI** que roda lint+types+testes+scanners.

---

# PARTE B — Detalhe técnico

## Evidência das ferramentas (§3)

| Ferramenta | Resultado | Observação |
|-----------|-----------|-----------|
| **ruff** 0.15 (lint) | **69 erros** | 39 E501 (linha longa), 14 B008 (Depends em default — idiom FastAPI, falso-positivo), 4 UP042 (str-enum), **2 F841 (variável não usada)**, etc. |
| **bandit** 1.8 (segurança) | **0 médio/alto** | só B101 (uso de `assert`) baixo — não pega RLS nem credencial |
| **npm audit** (frontend) | **1 alta + 1 moderada** | Next.js (SSRF/cache poisoning/middleware bypass) + postcss XSS; fix completo exige `next@16` (breaking) |
| **pip-audit** (backend) | **7 vulns em 5 pacotes** | starlette PYSEC-2026-161, python-multipart (3), pytest, black, python-dotenv |
| **segredos** (git + tree) | repo/histórico **limpos** | mas `.env` no disco tem a **senha real** do Sienge; e ela foi exposta no chat |
| **pytest + coverage** | **NÃO VERIFICADO** | sem Postgres e Python 3.9≠3.11 no ambiente — suíte não executada |
| **mypy** | **NÃO VERIFICADO** | não instalado; 3.9 nem avalia a sintaxe `X | None` do projeto |
| **semgrep / gitleaks / trufflehog** | **NÃO RODADOS** | indisponíveis (sem brew); usei grep+git-history como substituto parcial |

---

## CRÍTICOS

### C-1 — RLS ignorado: app conecta como superusuário → isolamento inativo
- **Onde:** [docker-compose.yml:6](../docker-compose.yml#L6) (`POSTGRES_USER: audit`), [.env.example:22](../.env.example#L22) (`DATABASE_URL=...audit:audit@...`), [backend/app/core/db.py:24](../backend/app/core/db.py#L24) (engine usa essa URL), [backend/app/tenancy/rls.py:22](../backend/app/tenancy/rls.py#L22) (`FORCE ROW LEVEL SECURITY`).
- **Evidência:** a imagem oficial do Postgres cria `POSTGRES_USER` como **superusuário**. Na doc do PostgreSQL: *"Superusers and roles with the BYPASSRLS attribute always bypass the row security system."* O `FORCE RLS` só força o RLS para o **dono da tabela**, **não** para superusuário. O docstring de `db.py` afirma o contrário ("A role da aplicação NÃO tem BYPASSRLS") — **falso na config entregue**.
- **Por que é problema:** todas as policies `tenant_id = current_setting('app.current_tenant')` são **puladas**. O `SET app.current_tenant` não tem efeito. Cliente A enxerga dado de B. É o risco existencial nº 1 do produto.
- **Como corrigir:**
  1. Criar role dedicado: `CREATE ROLE app_rw LOGIN PASSWORD ... NOSUPERUSER NOBYPASSRLS;` e conceder `SELECT/INSERT/UPDATE/DELETE` nas tabelas (sem ownership).
  2. App conecta com `app_rw`; migrações (Alembic) continuam com o role dono/admin.
  3. Adicionar **teste** que conecta como `app_rw` e prova que sem `app.current_tenant` não vê linhas, e que A não vê B (ver C-2).
  4. Defesa em profundidade: manter `FORCE RLS` e revisar que nenhum role de app tem `BYPASSRLS`.

### C-2 — Isolamento multi-tenant NÃO provado (suíte nunca executada)
- **Onde:** [backend/tests/test_isolation.py](../backend/tests/test_isolation.py) (existe), mas nenhuma execução ocorreu.
- **Evidência:** `pytest` exige Postgres + deps + Python 3.11; o ambiente só tem 3.9 e não tem banco. Nenhuma rodada de `make test` foi feita em lugar nenhum. Único verificado: byte-compile + testes **puros** (mapeadores/Money) — que não tocam isolamento.
- **Por que é problema:** o portão de produção (§8) exige isolamento **provado por teste**. Sem execução, e com C-1, o mais provável é que o teste **falharia** hoje. "Não testado" + "config furada" = não pode ir para cliente.
- **Como corrigir:** subir Postgres (ver `scripts/install_runtime.sh`), `make migrate`, `make test`, e bloquear release se `test_isolation` não passar com o role `app_rw` de C-1.

### C-3 — Credencial de produção do cliente exposta
- **Onde:** `.env:49` (`SIENGE_DEFAULT_PASSWORD=...`, working tree) + exposta no chat desta sessão.
- **Evidência:** `git ls-files .env` → não rastreado (✅ não está no repo nem no histórico). Mas a senha de API do Sienge da Alumbra trafegou em texto no chat e está em disco.
- **Por que é problema:** é a credencial de leitura do ERP de um cliente real. Exposição em canal de chat pode ser registrada/cacheada.
- **Como corrigir:** **rotacionar a senha de API no Sienge agora**; depois injetar só via secret manager. Confirmar que nenhuma cópia foi versionada (confirmado: histórico limpo).

---

## ALTOS

### A-1 — Risco de falso-positivo nas regras de fraude, sem métrica de erro
- **Onde:** [backend/app/rules/builtin.py](../backend/app/rules/builtin.py) — R3 `alcada=50000` fixo; R1 `threshold_pct=0.10`; R6/R2 dependem de `resourceId==productId`.
- **Evidência:** sondagem real mostrou **65/115** resourceIds com correspondência em productId — ou seja, **~43% dos insumos do pedido não aparecem nas cotações**; para esses, R6 marcaria "0 fornecedores cotando" possivelmente **indevidamente**. Não existe nenhuma medição de precisão/FP no código (o brief §8 exige).
- **Por que é problema:** mostrar a um cliente "compra sem concorrência" ou "sobrepreço" que é falso queima a confiança — o ativo central do produto.
- **Como corrigir:** (1) calibrar alçada por tenant (puxar de `order_authorization`/totalization real); (2) tratar "insumo sem produto cotável" diferente de "sem concorrência"; (3) instrumentar taxa de aceite/descarte por regra como métrica de FP.

### A-2 — Auditoria contínua não implementada (worker é stub)
- **Onde:** [backend/app/workers/run.py:18-23](../backend/app/workers/run.py#L18) — loop `while True: sleep(60)`, sem fila/scheduler.
- **Por que é problema:** a promessa "audita 100% continuamente" não acontece; só há disparo manual (`/rules/run`, `sync_alumbra`). Pior: pode **deixar de auditar sem avisar** (falha silenciosa de produto).
- **Como corrigir:** ligar APScheduler + RQ (já são dependências) com job de sync incremental por tenant + reavaliação via outbox; alertar se um tenant não sincroniza há X.

### A-3 — Falha silenciosa no ingest (sem dead-letter real, sem alerta)
- **Onde:** [backend/app/connectors/sienge/load.py](../backend/app/connectors/sienge/load.py) — `except Exception: log.warning(...)` ao puxar itens; continua. O `raw_record`/dead-letter descrito nos docs **não é populado** nesse caminho.
- **Por que é problema:** um pedido cujos itens falharam é auditado **incompleto** e ninguém é avisado → achados ausentes silenciosamente.
- **Como corrigir:** persistir falhas em tabela dead-letter por tenant + métrica/alerta; expor "cobertura do sync" (quantos pedidos/itens ficaram de fora).

### A-4 — Dependências vulneráveis e sem lockfile (build não reproduzível)
- **Evidência:** `npm audit` → 1 alta (Next.js) + 1 moderada (postcss); `pip-audit` → 7 vulns (starlette, python-multipart…). Backend usa `>=` em [backend/pyproject.toml](../backend/pyproject.toml) sem lock/hashes; frontend tem lock, mas com vuln pendente que exige major.
- **Como corrigir:** gerar lock determinístico (pip-tools/uv lock; commitar `package-lock`), atualizar pacotes, e rodar `pip-audit`/`npm audit` no CI.

---

## MÉDIOS

- **M-1 Sem CI/CD; pre-commit nunca executado.** [.pre-commit-config.yaml](../.pre-commit-config.yaml) existe mas gitleaks/ruff não estão instalados e nunca rodaram; nenhuma pipeline. *Corrigir:* GitHub Actions rodando ruff+mypy+pytest+coverage+bandit+pip-audit+gitleaks; pre-commit instalado.
- **M-2 mypy declarado (strict) mas nunca verificado.** Tipagem não garantida. *Corrigir:* rodar mypy no CI em Python 3.11.
- **M-3 Tipos de dinheiro enganosos.** Colunas monetárias são `Mapped[float]` com `Numeric(18,4)` ([backend/app/models/sourcing.py](../backend/app/models/sourcing.py)). O caminho canônico converte via `_dec(str())` (✅), mas a anotação `float` e os JSON floats que entram são frágeis; um caminho novo que esqueça `_dec` introduz erro de centavos. *Corrigir:* anotar `Decimal`, converter na borda, proibir float em valor.
- **M-4 Prompt injection / PII fraca nos agentes.** [backend/app/agents/llm.py](../backend/app/agents/llm.py) redige só CPF por regex; campos controlados pelo cliente (nome de fornecedor, `notes`) vão para o prompt. Agentes não têm tool de escrita (impacto contido), mas a narrativa pode ser manipulada. *Corrigir:* redigir CNPJ/email/nome quando desnecessário; delimitar/escapar dado no prompt; instrução anti-injeção.
- **M-5 R4 depende de medição lançada.** Se `measuredQuantity` não é preenchido na obra, R4 dá zero silencioso (na amostra real, R4=0). *Corrigir:* sinalizar obras sem medição em vez de assumir "tudo certo".
- **M-6 Ledger/gainshare sem teste de ponta.** `value_ledger` e baseline congelado não foram exercitados (suíte não rodou).
- **M-7 N+1 no carregamento.** [load.py](../backend/app/connectors/sienge/load.py) faz 1 chamada de itens por pedido (7.206 chamadas na base). *Corrigir:* usar bulk-data de itens se existir, ou paralelizar com limite + cache.

## BAIXOS

- **B-1** `analyze_alumbra.py` usa `float` para exibir R$ (é dry-run, aceitável, mas inconsistente com o padrão Decimal).
- **B-2** 2 variáveis não usadas (ruff F841); 39 linhas > 100 colunas; imports não ordenados.
- **B-3** Logs estruturados não têm scrubber explícito de PII (só "não logar de propósito").

---

## Portão de produção (§8) — checklist

| Requisito | Status |
|-----------|:------:|
| Zero achados CRÍTICOS | ❌ (3 críticos) |
| Isolamento multi-tenant **provado por teste** | ❌ (nunca executado; e provavelmente furado por C-1) |
| Nenhum segredo no código/histórico | ✅ repo/histórico limpos — ⚠️ mas credencial viva em `.env` + exposta no chat (rotacionar) |
| Suíte existe, passa e cobre caminhos críticos | ❌ (existe; **não passou porque não rodou**; sem cobertura) |
| Somente-leitura no ERP garantido | 🟡 por design (só GET; sem método de escrita) — **não testado** |

### Veredito: **NÃO PRONTO PARA CLIENTE.**

Para virar PRONTO, no mínimo: corrigir C-1 (role sem superusuário), **executar** a suíte com `test_isolation` passando (C-2), rotacionar a credencial (C-3), implementar dead-letter+alerta e ligar o worker (A-2/A-3), e estabelecer métrica de falso-positivo + calibração (A-1).

---

## O que este auditor NÃO conseguiu verificar (honestidade)

- Execução de `pytest`, cobertura, `mypy`, `semgrep`, `gitleaks` — ambiente sem Postgres/Docker e Python 3.9. **Recomendação:** repetir esta auditoria dentro do container (Python 3.11 + Postgres), onde tudo roda, antes de qualquer go-live. Até lá, os itens acima permanecem **NÃO VERIFICADOS por execução**, o que é, por si, motivo de não-prontidão.
