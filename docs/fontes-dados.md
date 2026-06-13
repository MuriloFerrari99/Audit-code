# Fontes de Dados — As 5 Dimensões

Cada dimensão de auditoria pergunta uma coisa e tem suas próprias fontes. Marcamos **dia-1 vs. depois** e **universal vs. vertical/cliente**. O núcleo universal (dimensões 2, 3, 4) é o que dá horizontalidade e prepara LATAM; a dimensão 1 é o pacote plugável por vertical; a 5 é configuração por cliente.

## Visão geral

| # | Dimensão | Pergunta | Tipo | Fase | Fonte de verdade |
|---|----------|----------|------|------|------------------|
| 1 | Preço | "Está caro?" | **Vertical/plugável** | MVP | interno + público (SINAPI...) + benchmark |
| 2 | Documento fiscal | "A nota é válida e bate?" | **Universal** | Fase 1 | NF-e/NFS-e + SPED + SEFAZ |
| 3 | Pagamento | "Pagou certo, 1x, conta certa?" | **Universal** | Fase 1 | contas a pagar + Open Finance |
| 4 | Contraparte | "Devo comprar dessa empresa?" | **Universal** | Fase 1 | CEIS/CNEP/CEPIM + Receita |
| 5 | Contrato/conformidade | "Respeitou contrato/política?" | **Por cliente** | Fase 2 | contrato + orçamento + política do cliente |

---

## Dimensão 1 — Preço (vertical, plugável) · **MVP**

**Pergunta:** o preço pago/cotado está acima do razoável?

**Arquitetura de pacote de preço plugável:** um `PricePackage` por vertical fornece a referência externa. O núcleo de comparação é o mesmo; troca-se o pacote.

| Vertical | Pacote de preço (fonte pública) |
|----------|--------------------------------|
| **Construção** (MVP) | **SINAPI** (Caixa/IBGE), **SICRO** (DNIT), **CUB** (Sinduscon por UF) |
| Saúde | Banco de Preços em Saúde + CMED |
| Agro | CEPEA/ESALQ, CONAB |
| Frota | FIPE, ANP (combustível), ANTT |
| Cross-setor | **Painel de Preços** + **PNCP** (compras públicas) |

Mais: **histórico do próprio cliente** (Camada 0) e **benchmark cross-cliente** (Camada 2 — o fosso).

**Fontes do MVP (dia-1):**
- **Interno (Camada 0):** mediana histórica de preço do próprio tenant por insumo.
- **SINAPI (Camada 1):** download mensal da Caixa, por UF (regional), mapeado por **código SINAPI** (que é a espinha do catálogo canônico — ver [ml.md](./ml.md)). `[ASSUNÇÃO]` SINAPI desonerado como referência default, configurável por tenant.
- **CUB (Camada 1):** referência macro por m², por UF — uso secundário/sanity-check.

**Pré-requisito:** casamento de insumo (descrição do cliente → `catalog_item` → código SINAPI). Sem isso não há comparação. É o problema duro de dado (ver [ml.md](./ml.md)).

---

## Dimensão 2 — Documento fiscal (universal) · **Fase 1**

**Pergunta:** a nota é válida (existe na SEFAZ, não é fria) e bate com o pedido?

**Fontes:**
- **NF-e / NFS-e:** XML que o próprio cliente **emite/recebe** (ele tem direito ao documento). Captura via:
  - `[ASSUNÇÃO]` **primário:** ingestão dos XMLs que o cliente já possui (ele é destinatário/emitente).
  - **secundário:** consulta de status na **SEFAZ** com **certificado digital** do cliente (cofre de certificados A1/A3 — abstrair desde já; ver [latam-readiness.md](./latam-readiness.md)).
- **SPED** (fiscal/contribuições): cruzamento de escrituração.
- **Validação SEFAZ:** chave de acesso, situação (autorizada/cancelada/denegada).

**O que pega:** nota fria, divergência pedido↔nota (qty/preço/CNPJ), imposto/crédito errado.

**Por que universal e estratégico:** toda a LATAM tem documento fiscal eletrônico padronizado (NF-e BR, CFDI MX, DIAN CO...). A mesma máquina de validação reusa por país trocando parser + feed. É o pilar da expansão (ver [estrategia.md](./estrategia.md) §6).

---

## Dimensão 3 — Pagamento (universal) · **Fase 1**

**Pergunta:** pagou o valor certo, uma única vez, na conta certa?

**Fontes:**
- **Contas a pagar do ERP** (`bill`/`payment`) — já no canônico desde o MVP.
- **Open Finance** (extrato/transações bancárias) via agregador. `[ASSUNÇÃO]` **Pluggy** como agregador de referência no Brasil (alternativa: Belvo, mais LATAM-wide — relevante para o foguete).

**O que pega:** pagamento duplicado, pagamento sem lastro (sem pedido/nota), **conta do fornecedor divergente** (sinal forte de fraude — cuidado redobrado, advisory).

---

## Dimensão 4 — Contraparte / integridade (universal) · **Fase 1**

**Pergunta:** eu deveria estar comprando dessa empresa?

**Fontes (públicas, grátis):**
- **CEIS** (Cadastro de Empresas Inidôneas e Suspensas) — CGU.
- **CNEP** (Cadastro Nacional de Empresas Punidas) — CGU.
- **CEPIM** (entidades privadas sem fins lucrativos impedidas) — CGU.
- **Situação cadastral do CNPJ** na Receita Federal.
- **Quadro societário** (QSA) — conflito de interesse, empresa-laranja, sócio em comum com comprador.
- Risco de crédito (fonte a definir — pode ser paga).

**O que pega:** fornecedor sancionado, CNPJ inapto, empresa recém-aberta de alto valor, sócio ligado a quem aprova a compra (conflito).

> **Cuidado redobrado:** esta dimensão toca reputação de pessoas/empresas. Sempre advisory, sempre com evidência da fonte oficial citada, sempre humano decide. Nunca rotular "fraude" automaticamente — rotular "sinal a investigar".

---

## Dimensão 5 — Contrato / conformidade (por cliente) · **Fase 2**

**Pergunta:** respeitou o contrato, o orçamento e a política da empresa?

**Fontes:** contrato com fornecedor, orçamento aprovado da obra, política de alçada/compras do cliente (configurável). É **por cliente** porque a regra é a política daquele cliente.

**O que pega:** compra fora de contrato vigente, estouro de orçamento, quebra de alçada/política, prazo/condição contratual violada.

---

## Resumo: o que entra no MVP

- **Dimensão 1 (preço)** com **Camada 0 (interno)** + **Camada 1 (SINAPI/CUB)**.
- As demais dimensões entram nas Fases 1–2, mas o **modelo canônico já as comporta** (campos fiscais, de pagamento e de integridade reservados — ver [modelo-dados.md](./modelo-dados.md)).
- O **benchmark (Camada 2)** começa a compor na Fase 1, quando houver volume e casamento de insumo.
