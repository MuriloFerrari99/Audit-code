# Estratégia — Vaca Leiteira → Foguete

## 1. Tese

Construtoras e incorporadoras compram muito, de forma fragmentada, e perdem **3–10% do custo de obra** em sobrepreço, desperdício, fracionamento de compra, falhas de medição e fraude de pagamento. Hoje auditam por amostra, manualmente, depois do dinheiro já ter saído.

Nós lemos o dado que a empresa **já tem** (ERP, notas fiscais eletrônicas, banco), auditamos **100% das transações continuamente** e devolvemos **achados com evidência anexa e o valor em R$ exposto**. Não substituímos o ERP — lemos o dado e pensamos em cima dele.

## 2. Identidade dupla

| Eixo | Vaca leiteira (agora) | Foguete (opção futura) |
|------|----------------------|------------------------|
| Capital | Bootstrapped, lucrativo, do founder | Venture, se a tração provar |
| Geografia | Brasil, vertical construção | LATAM (México/CFDI primeiro) |
| Cliente | SMB/mid construção (deal flow do founder) | Enterprise multi-empresa + horizontal multi-vertical |
| Infra | Lean, 1 servidor, conteinerizado | Cloud-native escalável |
| Prioridade | Caixa e ROI provado | Crescimento e fosso |

> **Regra de ouro:** *arquitete para a opção, construa para o agora.* Tome as decisões **baratas** que mantêm a porta aberta. Não construa o que ainda não foi decidido expandir.

## 3. As decisões baratas que mantêm a porta aberta

Estas são as escolhas de design que custam quase nada hoje e evitam um rewrite amanhã. São **invariantes** — entram no código do MVP mesmo sem nenhuma feature de expansão ser construída.

1. **Multi-tenancy e isolamento desde o dia 1.** Toda linha de dado carrega `tenant_id`. RLS no Postgres. (Detalhe em [modelo-dados.md](./modelo-dados.md).)
2. **Abstração de país no modelo de dados.** Campos `country_code`, `currency`, `tax_regime` em todas as entidades relevantes — mesmo que só exista `BR`/`BRL` hoje.
3. **Abstração de vertical.** O catálogo de insumos, o pacote de preço e as regras de "preço caro" são plugáveis por `vertical` (construção hoje; saúde/agro/frota depois).
4. **Conectores como plugins.** Ingestão é uma interface (`SourceConnector`); Sienge é a primeira implementação. NF-e, Open Finance, CGU/Receita são implementações futuras da mesma interface.
5. **Benchmark cross-cliente anonimizado já no design.** A separação entre "dado identificável do tenant" e "agregado anonimizado para o pool" existe no schema desde já, mesmo antes de o benchmark ser ligado. (Ver [ground-truth.md](./ground-truth.md) e [seguranca-lgpd.md](./seguranca-lgpd.md).)
6. **Núcleo universal vs. pacote plugável.** Das 5 dimensões de auditoria, 3 são universais (fiscal, pagamento, contraparte) e 1 é plugável por vertical (preço) e 1 por cliente (contrato). (Ver [fontes-dados.md](./fontes-dados.md).)

## 4. O que NÃO construir agora (anti-escopo)

Para preservar a vaca leiteira, estes itens ficam **explicitamente fora** até um gate de decisão liberar:

- Billing multi-país / multi-moeda real (só BR/BRL).
- Localização de UI (só pt-BR).
- Infra global / multi-região.
- Conectores de outros ERPs além do Sienge.
- Conectores de outros países (CFDI/DIAN etc.) — apenas a **abstração** existe.
- Dimensões 2–5 completas no MVP (entram nas Fases 1+). MVP = dimensão de preço + auto-consistência.
- App mobile nativo (web responsivo basta).

## 5. Gates de decisão (vaca → foguete)

Cada transição de fase é um **gate** com critério objetivo. Não se avança por entusiasmo; avança-se por evidência.

| Gate | De → Para | Critério de passagem |
|------|-----------|----------------------|
| **G0** | — → MVP | Cliente zero (construtora do founder) integrado, 6 regras rodando sobre dado real |
| **G1** | MVP → Auditoria completa BR | R$ real achado e validado pelo cliente zero + ≥2 clientes pagantes |
| **G2** | Completa → Horizontal BR | Repetibilidade fora da construção (1 vertical novo onboarda em < X semanas) |
| **G3** | Horizontal → Foguete/LATAM | Tração + ARR mínimo + decisão de capital + 1 cliente LATAM identificado |

Detalhe operacional dos gates em [roadmap.md](./roadmap.md).

## 6. Por que LATAM é a expansão natural (contexto, não escopo)

A LATAM é **líder mundial em nota fiscal eletrônica**: Brasil (NF-e/NFS-e), México (CFDI), Chile, Colômbia (DIAN), Peru. Isso torna a **dimensão fiscal padronizada** em toda a região — a mesma máquina de validação de documento fiscal que construirmos para o Brasil se reusa, trocando só o parser e o feed local. É por isso que a dimensão fiscal é tratada como **universal** no núcleo, mesmo sendo Fase 1: ela é o ativo de expansão.

## 7. O fosso (moat)

O ativo que compõe com o tempo é o **benchmark proprietário de preços realmente transacionados**, agregado e anonimizado entre clientes. Cada cliente novo melhora a referência de preço para todos — sem nunca expor o preço identificável de um cliente a outro.

O fosso **não é requisito de largada** (Camada 2 da estratégia de verdade) e **não é um banco que se compra**. Ele se constrói a partir do dado que flui pela plataforma. O design protege isso desde já (ver [seguranca-lgpd.md](./seguranca-lgpd.md) §anonimização). Pré-requisito técnico do fosso: **casamento de insumos para um catálogo canônico** (ver [ml.md](./ml.md)).

## 8. Resumo executivo da estratégia

- Comece estreito e fundo: **suprimentos de construção no Brasil**, cliente zero é a construtora do founder.
- Cobre por valor: **mensalidade base + gainshare** (ver [gtm.md](./gtm.md)).
- Arquitete o **núcleo universal** + **plugins** para que horizontalizar seja configurar, não reescrever.
- Proteja o **fosso** (benchmark) no design desde o dia 1, mesmo desligado.
- Avance por **gates objetivos**, não por hype.
