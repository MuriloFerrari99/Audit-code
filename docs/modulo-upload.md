# Plano — Ingestão por Upload (XML NF-e/NFS-e + planilha ERP)

> Core definido pelo founder: subir XMLs e planilhas e auditar — para **qualquer**
> construtora, sem depender de conector de ERP. Alimenta o MESMO modelo canônico
> e as MESMAS regras já existentes (preço, fiscal, pagamento, integridade).

## Por que isso destrava o produto
Hoje a ingestão é via API do Sienge (ótimo p/ quem usa Sienge). O upload abre o
SaaS para **qualquer empresa**: ela exporta os XMLs (que já recebe/emite) e uma
planilha de lançamentos, sobe, e recebe a auditoria. Sienge vira "um dos conectores".

## Fontes e o que é parseável
| Fonte | Padrão | Parseável nacionalmente? |
|------|--------|--------------------------|
| **NF-e** (mercadoria) | XML 4.00 nacional (namespace portalfiscal) | ✅ sim — um parser serve todos |
| **NFS-e** (serviço) | **fragmentado** (ABRASF + variações por município) | ⚠️ parcial — parser ABRASF + adaptadores por layout |
| **Planilha ERP** (lançamentos) | livre por ERP | mapeamento de colunas (template + assistente) |

## Campos da NF-e (o que extraímos)
- Cabeçalho: `chave` (Id 44 díg.), `nNF`, `serie`, `dhEmi`, `natOp`, emitente (CNPJ/nome), destinatário.
- Itens (`det/prod`): `cProd`, `xProd`, `NCM`, `CFOP`, `uCom`, `qCom`, `vUnCom`, `vProd`.
- Totais/tributos: `vProd`, `vICMS`, `vIPI`, `vNF`.
- **Retenções** (diferencial INSS/ISS): `total/retTrib` (`vRetPIS/COFINS/CSLL`, `vIRRF`, **`vRetPrev`=INSS**) e ISS (`ISSQN/vISSRet`, `ISSQNtot`).

## Como liga ao que já existe
- Cabeçalho NF-e → entidade canônica **`invoice`** (número, série, valor, tributos, chave, fornecedor) — já temos.
- Itens da nota → **price audit** (sobrepreço por insumo) — precisa de uma entidade de **item de nota** (novo) OU reaproveitar o casamento de insumo.
- Planilha de lançamentos → **bill/payment** + pedidos → regras de pagamento/divergência.
- Cruzamento nota↔lançamento → divergências (F1/F3) e **retenções** (regras novas).

## Regras novas habilitadas
- **Retenção INSS** errada/ausente em serviço (NFS-e/NF-e `vRetPrev`).
- **Retenção ISS** errada (alíquota/base) — `ISSQN`.
- Cruzamento valor da nota × lançamento × pagamento.

## Rollout (incremental, verificável)
1. **Parser NF-e** (puro, testado contra XML real) — *este passo*.
2. Entidade de **item de nota** + carga upload → canônico (tenant-scoped).
3. **Endpoint de upload** (multipart: XMLs/zip + planilha) + status.
4. **Parser de planilha** (CSV/XLSX) com mapeamento de colunas.
5. **NFS-e** (ABRASF + adaptadores) e **regras de retenção** (INSS/ISS).
6. **UI**: tela de upload (arrastar XML/zip + planilha) → auditoria.

## Invariantes
Mesmos de sempre: tenant-scoped (RLS), evidência + confiança, advisory, nunca
falhar em silêncio (XML inválido → dead-letter visível), LGPD.
