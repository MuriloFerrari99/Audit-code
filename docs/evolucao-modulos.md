# Evolução dos Módulos — de "auditoria básica" a produto que entrega valor

## Diagnóstico honesto sobre "Deep Learning"

O pedido é "montar Deep Learning para o sistema não jogar dado burro". A verdade técnica:

- **DL não é o primeiro passo.** Aprendizado supervisionado precisa de **rótulos** (o humano aceitando/descartando achados). Hoje temos **zero rótulos**. DL sem rótulo não aprende nada útil.
- **DL em cima de dado sujo aprende sujeira.** O Sienge da Alumbra tem cotação R$ 0, código de insumo genérico ("MAO DE OBRA" misturando R$ 3,7k e R$ 150k), itens sem código. Qualquer modelo treinado nisso reproduz o lixo.
- **O que realmente evita "dado burro"** (em ordem de impacto e maturidade):

| # | Camada | O que faz | Estado |
|---|--------|-----------|--------|
| 1 | **Higiene de dados** | sanitiza o Sienge na origem (o que checar/corrigir) | **este doc — construindo** |
| 2 | Filtros por natureza | material×serviço, dispersão, ratio | ✅ feito (auditoria A-1) |
| 3 | **Score de confiança** | cada achado leva uma confiança (features) | **construindo** |
| 4 | Loop de feedback → calibração por tenant | aceitar/descartar vira rótulo; thresholds por empresa | encaixe pronto (finding_review) |
| 5 | Modelo aprendido / embeddings | quando houver volume de rótulos: ranking ML + casamento de insumo p/ benchmark | futuro (depende de 4) |

"Os filtros que cada empresa usa" = **calibração por tenant** (cada empresa tem sua alçada, suas categorias de material, seus thresholds) — configurável e, com o tempo, **aprendida do feedback**. É isso que substitui o "DL mágico" por algo que funciona.

## Módulo A — Higiene de Dados (sanitização do Sienge)

Entrega ao cliente **a lista de lançamentos a checar/corrigir no Sienge** — e, de quebra, **derruba o ruído da auditoria na origem**. Checagens (sobre o dado real):

| Código | Problema | Por que importa |
|--------|----------|-----------------|
| DQ1 | Item sem `resourceId` / sem preço / preço = 0 | não dá para auditar; polui mediana |
| DQ2 | `resourceId` genérico (preço com dispersão alta) | mistura itens → sobrepreço falso; **desmembrar cadastro** |
| DQ3 | Cotação com preço R$ 0 (placeholder) | gera "cotação perdida" falsa |
| DQ4 | Pedido relevante sem cotação registrada | governança + impede comparação |
| DQ5 | Orçamento sem medição lançada (obra ativa) | impede achado de estouro; medição atrasada |
| DQ6 | Fornecedor duplicado (mesmo CNPJ, ids diferentes) | distorce histórico e concorrência |

Saída: severidade + entidade + id + ação recomendada ("preencher código", "desmembrar insumo", "lançar medição", "unificar fornecedor").

## Módulo B — Score de confiança por achado

Cada achado recebe `confidence ∈ [0,1]` a partir de **features explicáveis**:
- tamanho da amostra (n) da referência; dispersão do insumo; camada da referência (SINAPI > mediana); se é material; ratio pago/referência; recência.
- Achados de **baixa confiança** saem da fila principal (vão para "a investigar"), não para o cliente. É o que impede "dado burro" de chegar na cara do cliente — **hoje, sem DL**.

## Módulo C — Loop de feedback → calibração por tenant (prepara o ML)

- Cada `finding_review` (aceitar/descartar/justificar) é um **rótulo**.
- Calibração por tenant: se uma empresa descarta sistematicamente uma faixa, o threshold sobe **para ela** (não global).
- Quando o volume de rótulos justificar: treinar um **ranker** (gradient boosting nas features de confiança) por vertical, e **embeddings** para casamento de insumo (pré-requisito do benchmark cross-cliente). **Aí sim** entra "aprendizado profundo", com base limpa e rótulos reais.

## Módulos de cruzamento (dimensões 2–4, próximas ondas)

Já previstos em [fontes-dados.md](./fontes-dados.md); o núcleo canônico já comporta:
- **Fiscal (NF-e):** nota fria, divergência pedido↔nota.
- **Pagamento (Open Finance):** duplicado, conta divergente.
- **Contraparte (CEIS/CNEP/Receita):** fornecedor sancionado/laranja/conflito.

## Entrega desta etapa
1. Módulo A (Higiene) **rodando sobre o Sienge real** + versão produto (`app/quality`).
2. Módulo B (confiança) no motor de regras + no dry-run.
3. Módulo C: caminho de calibração por tenant documentado e com hook em `finding_review`.
