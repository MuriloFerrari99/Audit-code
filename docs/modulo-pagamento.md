# Plano — Módulo Pagamento (Dimensão 3)

> "Pagou certo, uma vez, na conta certa?" Fontes validadas no Sienge real (2026-06-14).

## Descoberta
- Título (`/bills`): `documentNumber`, `documentIdentificationId`, `installmentsNumber`,
  `totalInvoiceAmount`, `creditorId`, `status`. → **duplicado detectável sem confundir parcela**.
- `creditors/{id}/bank-informations` veio **vazio** → conta cadastrada nem sempre existe;
  e a **conta realmente paga** não está no Sienge → "conta divergente" exige **Open Finance**.

## Fases

### Fase A — do Sienge (sem agregador) — **executando agora**
| Regra | Dispara | Confiança |
|------|---------|-----------|
| **P1 Pagamento duplicado** | ≥2 títulos com mesmo (fornecedor, documento, identificação, valor) | média (validar) |
| **P2 Pagamento sem lastro** | título sem pedido vinculado **e** sem nota vinculada | média |
| (R5 já existe) | pago acima do pedido | alta |
| (F3 já existe) | pago acima da nota | alta |

### Fase B — Open Finance (agregador + consentimento) — **gated**
| Regra | Dispara | Pré-requisito |
|------|---------|---------------|
| **P3 Conta divergente** (fraude) | conta paga ≠ conta esperada do fornecedor | Pluggy/Belvo + consentimento bancário |
| **P4 Pagamento fora do ERP** | transação bancária sem título correspondente | idem |

## Invariantes
- Advisory + evidência (títulos citados); **nunca falhar em silêncio**.
- P1 tem risco de falso-positivo (parcelas/refaturamento) → confiança **média** + chave por documento; calibrável por tenant.
- Read-only; isolamento; LGPD (dado bancário na Fase B é sensível — consentimento explícito).

## Open Finance (Fase B) — decisão futura
Exige: conta no **Pluggy** (BR) ou **Belvo** (LATAM), credenciais via SecretProvider, e o
**fluxo de consentimento** do cliente (OAuth do banco). Não dá para validar/ligar sem isso —
por isso fica gated, como a chave do Sienge/CEIS e o certificado NF-e.

## Rollout
1. Bill canônico ganha `document_number`/`document_identification` (migração) + carga.
2. P1/P2 + confiança + registro.
3. Fase B quando houver agregador + consentimento.
