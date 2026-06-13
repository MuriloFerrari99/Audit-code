# Perguntas em Aberto e Assunções

> Registro vivo. **Respondidas** = decididas pelo founder. **Assunções** = sigo com o default e marco; confirme ou ajuste quando puder. **Pendentes** = preciso de você antes de avançar no item.

## 1. Decisões já tomadas (founder)

| # | Decisão |
|---|---------|
| ✅ | Base real do Sienge desde o dia 1 (API, Basic Auth por subdomínio) |
| ✅ | Tenant = grupo/incorporadora → empresas (CNPJ) → empreendimentos/obras |
| ✅ | Isolamento: RLS em schema compartilhado no MVP → schema-per-tenant no enterprise |
| ✅ | Embeddings via API externa; produto online com atualização em tempo real |
| ✅ | Deploy: local nesta máquina → servidor próprio; conteinerizado e cloud-agnóstico |
| ✅ | Gainshare nível Big4 (metodologia completa em [gtm.md](./gtm.md)) |
| ✅ | Frontend desenhado com Claude Design |
| ✅ | LGPD: estrutura proposta do zero (em [seguranca-lgpd.md](./seguranca-lgpd.md)) |
| ✅ | Detalhes operacionais (rate limit, retry, scheduler, janelas) ficam comigo |
| ✅ | Eu desenvolvo; quando vier o PoC, incorporo e refatoro |

## 2. Assunções (sigo com o default; confirme quando puder)

| # | Tema | Default que adotei | Onde |
|---|------|--------------------|------|
| A1 | k-anonimato do benchmark | ≥3 tenants **e** ≥5 fornecedores por célula | [seguranca-lgpd.md](./seguranca-lgpd.md), [modelo-dados.md](./modelo-dados.md) |
| A2 | Cold-start de preço | % fixo configurável + mediana própria + SINAPI até o benchmark amadurecer | [ground-truth.md](./ground-truth.md), [regras.md](./regras.md) |
| A3 | Secret manager no servidor | auto-hospedável (Vault/Infisical) atrás de `SecretProvider` | [seguranca-lgpd.md](./seguranca-lgpd.md) |
| A4 | Alertas no MVP | e-mail + dashboard; WhatsApp na Fase 1 | [prd.md](./prd.md), [roadmap.md](./roadmap.md) |
| A5 | Captura NF-e (Fase 1) | XML que o cliente já possui (primário) + SEFAZ via certificado (secundário) | [fontes-dados.md](./fontes-dados.md) |
| A6 | Open Finance (Fase 1) | Pluggy como agregador de referência (Belvo se for priorizar LATAM) | [fontes-dados.md](./fontes-dados.md) |
| A7 | SINAPI desonerado | usar desonerado como default, configurável por tenant | [fontes-dados.md](./fontes-dados.md) |
| A8 | Thresholds default das 6 regras | sobrepreço 10%, fracion. 30d/10%/N≥2, estouro 5%, divergência 0–2% | [regras.md](./regras.md) |
| A9 | Lookback de gainshare | correção em até 90 dias do achado para atribuição | [gtm.md](./gtm.md) |
| A10 | Stack | Python/FastAPI, Postgres+pgvector, Redis+RQ, Next.js/TS, Docker Compose | [arquitetura.md](./arquitetura.md) |
| A11 | Modelos LLM | forte (Opus) p/ Investigador/Narrador; Haiku p/ Casador/Triador de volume | [agentes.md](./agentes.md) |
| A12 | Janela de backfill | 12–24 meses na carga inicial; intervalo de sync incremental ~15 min | [conector-sienge.md](./conector-sienge.md) |

## 3. Pendentes — preciso de você (não bloqueiam os docs; bloqueiam parte do código)

| # | Pergunta | Por que importa | Quando preciso |
|---|----------|-----------------|----------------|
| Q1 | **Credenciais reais do Sienge** (subdomínio + usuário/senha de API somente-leitura do cliente zero) | Validar o conector e o mapeamento campo a campo contra a base real | Início da implementação do conector |
| Q2 | **Motor Python do PoC** | Incorporar/refatorar as 6 regras em vez de recomeçar; fixar `regras.md` ao seu código | Antes de implementar o motor de regras |
| Q3 | **Percentuais do gainshare** (% sobre a base, cap, piso de materialidade, escalonamento) | Fechar a estrutura comercial e o `value_ledger` | Antes de faturar o 1º cliente |
| Q4 | **Confirmar A1–A12** ou ajustar | São defaults sensatos, mas alguns são opinativos (k-anon, thresholds, lookback) | A qualquer momento; ajusto sem rework grande |
| Q5 | **Minuta de DPA/contrato** existente? | Se houver, alinho; se não, redijo a partir da estrutura proposta | Antes do 1º cliente pagante |
| Q6 | **Servidor de produção** (qual provedor/host você pretende usar depois) | Ajustar o `SecretProvider`, backups e reverse proxy ao alvo real | Antes do deploy em servidor |
| Q7 | **Acesso REST + Bulk Data** do cliente zero (ambos habilitados?) | Estratégia de sync (bulk p/ cotações vs. REST) depende disso | Início do conector |

## 4. Como vou tratar os pendentes

- Sigo construindo tudo o que **não** depende dos pendentes (modelo canônico, motor de regras com dados sintéticos, dashboard, isolamento, ledger).
- Os itens Q1/Q2/Q7 entram assim que você me passar credenciais e o PoC.
- Q3/Q5 são comerciais/jurídicos — desenho o sistema para acomodá-los como configuração, sem travar a engenharia.
