# Plano — Módulo C: Calibração por empresa (aprende com o feedback)

> "Os filtros que cada empresa usa" + "não jogar dado burro", de forma honesta:
> estatística/heurística sobre os rótulos humanos — **não** Deep Learning prematuro.
> DL/ranker entra quando o volume de rótulos justificar; este módulo PRODUZ e USA
> os rótulos.

## Como funciona

1. **Rótulo**: cada `finding_review` (aceitar/descartar/escalar) já é um rótulo por tenant.
2. **Estatística por (tenant, regra)**: taxa de aceite/descarte, nº de amostras.
3. **Calibração de confiança**: um `confidence_factor ∈ [0.5, 1.1]` por (tenant, regra),
   derivado da taxa de aceite. O engine multiplica a confiança-base por esse fator →
   regra que a empresa sempre descarta **perde confiança** (vai para "a investigar"),
   regra que ela sempre aceita ganha. Reduz "dado burro" **por empresa**, sem DL.
4. **Sugestões (humano aprova)**: com amostra suficiente, sugere ajustar threshold ou
   desligar a regra para aquele tenant — nunca muda sozinho em silêncio.

## Invariantes
- **Mínimo de amostras** (default 10 reviews por regra) antes de calibrar — senão fator 1.0.
- **Nunca altera threshold automaticamente**; só **sugere** (decisão humana).
- A confiança calibrada é **explicável** (fator + amostras no snapshot).
- Por tenant (RLS); não vaza aprendizado entre empresas.

## Entrega
- Tabela `rule_calibration(tenant, rule, samples, accepted, dismissed, acceptance_rate,
  confidence_factor)`.
- `calibration.recompute(tenant)`: recalcula da base de reviews → upsert + sugestões.
- Engine aplica `confidence_factor` ao gravar o achado.
- API: `GET /calibration` (stats + sugestões), `POST /calibration/recompute`.

## Caminho para ML (futuro, com base limpa)
Quando houver muitos rótulos: treinar um **ranker** (gradient boosting) nas features
de confiança por vertical, e embeddings para casamento de insumo (benchmark). Este
módulo é o substrato.
