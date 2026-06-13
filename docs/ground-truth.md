# Estratégia de "Verdade" (Ground Truth) — 4 Camadas

## Conceito central

> Auditoria **não declara verdade absoluta** — aponta **desvio de uma referência**, mostra a **evidência**, e o **humano julga**.

Precisamos de três coisas, não de onisciência:
1. uma **referência** (contra o que comparar),
2. **explicabilidade** (mostrar a evidência do desvio),
3. **humano no loop** (decisão final é da pessoa).

Não existe um "banco mágico" de preços certos para comprar. A verdade vem em **camadas**, cada uma com custo e maturidade diferentes. As regras declaram de qual camada tiram sua referência.

## Camada 0 — Auto-consistência interna · **dia 1, zero base externa**

O próprio dado do cliente é a referência. Não precisa de nada de fora. **5 das 6 regras do MVP vivem aqui.**

| Regra | Referência interna |
|-------|--------------------|
| Cotação perdida | a cotação válida mais barata que **já existe** no próprio dado |
| Divergência pedido→pagamento | o **valor do próprio pedido** |
| Estouro de quantidade | a **quantidade orçada** da própria obra |
| Fracionamento | a **alçada vigente** + a janela de pedidos do próprio tenant |
| Sem concorrência | a **política/relevância** + ausência de cotações concorrentes no próprio dado |
| Sobrepreço (parcial) | a **mediana histórica do próprio cliente** por insumo |

**Força:** funciona no dia 1, sem dependência externa, e é altamente explicável ("você tinha uma cotação de R$ X e comprou por R$ Y"). **Limite:** não compara entre empresas nem contra mercado.

## Camada 1 — Bases públicas · **dia 1, grátis**

Referências públicas, baixadas ou via API pública. Complementam o sobrepreço e habilitam a dimensão integridade.

| Fonte | Uso | Acesso |
|-------|-----|--------|
| **SINAPI / CUB / SICRO** | preço de referência construção | download mensal / arquivo |
| **Painel de Preços** | preços de compras públicas (cross-setor) | portal/dataset |
| **PNCP** | contratações públicas | API pública |
| **CEIS / CNEP / CEPIM** | integridade de fornecedor (Fase 1) | API CGU gratuita |
| **Receita (situação CNPJ)** | idoneidade cadastral (Fase 1) | consulta |

**MVP usa:** SINAPI (principal) + CUB (sanity). As de integridade entram na Fase 1.

**Força:** referência de mercado neutra e pública, sem custo de dado. **Limite:** SINAPI é referência teórica/composição, nem sempre reflete o preço realmente praticado na região/volume — por isso a Camada 2.

## Camada 2 — Benchmark proprietário cross-cliente · **compõe com o tempo (o fosso)**

Preço **realmente transacionado**, agregado e anonimizado entre clientes. Cada cliente novo melhora a referência para todos.

- **Não é requisito de largada.** Liga quando há volume + casamento de insumo confiável.
- **Anonimização rígida:** só entra célula com **k-anonimato** (`[ASSUNÇÃO]` ≥3 tenants, ≥5 fornecedores). Preço identificável de um cliente **nunca** vaza para outro. Schema fisicamente separado, sem `tenant_id`. (Ver [seguranca-lgpd.md](./seguranca-lgpd.md) e [modelo-dados.md](./modelo-dados.md) §8.)
- **Pré-requisito:** casamento de insumo → catálogo canônico (ver [ml.md](./ml.md)).

**Força:** é a referência mais valiosa (preço real, não teórico) e o moat que compõe. **Limite:** demanda massa de dado e governança de privacidade impecável.

## Camada 3 — Feedback humano vira rótulo · **contínuo**

Cada decisão de revisão (**aceitar / descartar / justificar / escalar**) é um rótulo.

- Treina o ML (precisão do casamento de insumo, banda do benchmark, ranking de anomalia).
- **Calibra thresholds por cliente** (ex.: se um tenant descarta sistematicamente achados de sobrepreço < 8%, o threshold sobe para ele).
- Reduz falso-positivo ao longo do tempo → aumenta confiança → aumenta valor percebido.

**Força:** o sistema fica mais certeiro por cliente e no agregado. **Limite:** precisa de UX de revisão boa (atrito baixo) para gerar rótulo de qualidade.

## Como uma regra escolhe sua referência

Cada regra declara uma **cascata de referência** com fallback:

```
sobrepreço:
  preferir  → Camada 2 (benchmark, se k-anonimato e cobertura suficientes)
  senão     → Camada 1 (SINAPI regional do insumo)
  senão     → Camada 0 (mediana histórica do próprio cliente)
  severidade ajustada pela qualidade/idade da referência
```

**Cold-start** (`[ASSUNÇÃO]`): enquanto não há volume para a banda aprendida (Camada 2), o sobrepreço usa **% fixo configurável + mediana própria (Camada 0)** e/ou SINAPI (Camada 1). À medida que o benchmark amadurece, a banda aprendida substitui o % fixo.

## Princípio de explicabilidade da referência

Todo achado registra **qual camada e qual valor de referência** usou, no `finding_evidence`. O usuário sempre vê: "comparado contra **[SINAPI 95% PR, jun/2026]** / **[sua mediana 2025]** / **[benchmark anonimizado N=12]**". Nunca "o sistema achou caro".
