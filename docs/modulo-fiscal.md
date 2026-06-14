# Plano — Módulo Fiscal / Documento (Dimensão 2)

> "A nota é válida e bate com o pedido?" Pilar universal e **base da expansão LATAM**
> (NF-e BR → CFDI MX é a mesma máquina, troca o parser/feed).
> Fontes **validadas contra o Sienge real da Alumbra** (2026-06-14).

## 1. Descoberta-chave: a maior parte sai do Sienge, SEM certificado

`/purchase-invoices` (8.294 notas) já traz os campos fiscais:

| Sinal | Campo Sienge |
|------|--------------|
| Nº / série / sequencial | `number`, `series`, `sequentialNumber` |
| Emissão | `issueDate` |
| Fornecedor / empresa | `supplierId`, `companyId` |
| Valor produtos / total | `productsAmount`, `itemsTotalAmount` |
| **NF-e** (id/valor) | `eletronicInvoiceId`, `eletronicInvoiceAmount` |
| **Tributos** | `ipiTax`, `icmsStTax`, `differenceIpiAmount` |
| Vínculo ao pagamento | `billId` |
| **Consistência (Sienge)** | `consistency` (S/N) |

`deliveries-attended` liga **item do pedido ↔ item da nota** (`purchaseOrderId`, `purchaseOrderItemNumber`, `quantityDelivery`, `sequentialNumber`).

→ Dá para fazer **divergência pedido↔nota, nota↔pagamento, tributo e nota inconsistente** **sem certificado digital**. "Nota fria" (validar autorização na SEFAZ) é a única parte que exige certificado.

## 2. Fases

### Fase A — Fiscal pelo dado do Sienge (sem certificado, baixo atrito) — **prioridade**
| Regra | Dispara | Severidade |
|------|---------|-----------|
| **F1 Divergência pedido↔nota** | valor/qtd da nota acima do pedido vinculado | alta |
| **F2 Nota inconsistente** | `consistency = 'N'` (flag do próprio Sienge) | média |
| **F3 Divergência nota↔pagamento** | título (`billId`) pago acima da nota | alta |
| **F4 Documento não-eletrônico** | `eletronicInvoiceId` nulo em operação que deveria ter NF-e | média |
| **F5 Tributo atípico** | `ipiTax`/`icmsStTax` fora da faixa do histórico do insumo/fornecedor | média (heurística) |

### Fase B — Nota fria / validação SEFAZ (exige certificado A1/A3) — depois
| Regra | Dispara | Pré-requisito |
|------|---------|---------------|
| **F6 Nota fria/cancelada/denegada** | chave NF-e não autorizada na SEFAZ | **cofre de certificado** do cliente |

## 3. Modelo canônico (reuso + extensão)
A entidade `invoice` já existe (com `nfe_key`, `nfe_status`, `total_invoiced`, `qty_delivered`). Estender o mapeamento para os campos reais: `number/series`, `value` (`eletronicInvoiceAmount`/`itemsTotalAmount`), `ipi`/`icms`, `consistency`, `eletronicInvoiceId`, `bill_id`, `supplier_id`, e itens via `deliveries-attended` (qtd atendida por item de pedido). Tudo tenant-scoped (RLS).

## 4. Invariantes (iguais aos outros módulos)
- **Advisory + evidência**: cada achado cita a nota (nº, data, valor) e o que comparou.
- **Nunca falhar em silêncio**: nota sem vínculo ao pedido → "não conciliada" (visível), não ignorada.
- **Confiança**: F2 (flag do Sienge) e F1/F3 (cadeia direta) = alta; F5 (tributo heurístico) = média.
- **Read-only**; isolamento por tenant; LGPD.
- **Fase B (certificado)**: cofre dedicado A1/A3 criptografado, por tenant, acesso auditado (já previsto em seguranca-lgpd.md).

## 5. LATAM-readiness
A entidade fiscal canônica é neutra; F1–F5 independem do país. Trocar BR→MX = novo **parser** (CFDI) + feed da autoridade (SAT). Por isso a dimensão fiscal é o pilar de expansão.

## 6. Rollout (incremental, verificável)
1. Estender `invoice` + carga de `purchase-invoices` + `deliveries-attended` (parser validado contra dado real).
2. Regras F1/F2/F3 (maior valor, dado direto) → confiança alta.
3. F4/F5 (heurísticas) com calibração.
4. Fase B (SEFAZ) quando houver certificado.
5. UI: aba "Fiscal" + selo de consistência no dossiê.

## 7. Decisão para você (antes de executar)
- **Q-Fiscal:** começo pela **Fase A (sem certificado)** — F1/F2/F3 já entregam "a nota bate com o pedido e o pagamento?" usando o dado do Sienge — e deixo "nota fria/SEFAZ" (Fase B) para quando você disponibilizar o **certificado digital** do cliente? *(Recomendo: sim — valor real agora, atrito zero.)*
