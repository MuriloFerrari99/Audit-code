# LATAM-Readiness

> **Não construímos multi-país agora.** Este documento lista apenas **o que abstrair hoje** (decisões baratas) para que, quando o gate G3 liberar o foguete, expandir seja *novo conector + pacote de preço local + feed de sanções local* — nunca um rewrite. Entregamos só o Brasil.

## 1. Por que LATAM é a expansão natural

A LATAM é líder mundial em **nota fiscal eletrônica**: Brasil (NF-e/NFS-e), México (CFDI), Chile (DTE), Colômbia (DIAN), Peru, etc. A dimensão fiscal é, portanto, **padronizada na região**. A mesma máquina de validação de documento fiscal que construirmos para o Brasil se reusa por país, trocando parser + feed. Esse é o ativo de expansão — por isso a dimensão fiscal é **universal** no núcleo (ver [fontes-dados.md](./fontes-dados.md) e [estrategia.md](./estrategia.md) §6).

## 2. Os 5 pontos de abstração (baratos, feitos agora)

### 2.1 País no modelo de dados
- `country_code` e `currency` em toda entidade relevante (só `BR`/`BRL` hoje). (Ver [modelo-dados.md](./modelo-dados.md) §5.)
- `tax_regime` / atributos fiscais reservados na entidade fiscal.
- **Custo hoje:** ~zero (colunas com default). **Evita:** migração dolorosa depois.

### 2.2 Conectores como plugins
- Interface `SourceConnector` com `source_name` + `country_code`. Sienge (BR) é a 1ª implementação. (Ver [conector-sienge.md](./conector-sienge.md) §7.)
- Adicionar México = nova implementação (ERP local + CFDI), mesma interface.

### 2.3 Pacote de preço plugável por vertical **e** por país
- `PricePackage` resolve a referência de preço. Hoje: construção/BR (SINAPI/CUB/SICRO).
- México/construção = outro pacote (referência local). A regra de "está caro?" não muda; o pacote sim. (Ver [regras.md](./regras.md) e [fontes-dados.md](./fontes-dados.md).)

### 2.4 Feed de integridade/sanções por país
- Dimensão 4 (contraparte) lê um **feed de sanções/idoneidade** abstraído. BR: CEIS/CNEP/CEPIM/Receita.
- México/outros: feeds locais equivalentes — mesma interface de "checagem de contraparte".

### 2.5 Documento fiscal abstraído
- A entidade fiscal canônica é neutra; o **parser** é por país (NF-e XML hoje; CFDI XML depois).
- Validação (existe na autoridade fiscal? bate com pedido?) é a mesma lógica; muda o conector à autoridade (SEFAZ → SAT no México).

## 3. O que NÃO fazer agora (anti-escopo de expansão)

- Não construir billing multi-moeda/multi-país.
- Não localizar a UI (só pt-BR).
- Não implementar nenhum conector/parser/feed de outro país.
- Não montar infra multi-região.
- Não generalizar prematuramente além dos 5 pontos acima (YAGNI).

## 4. Privacidade multi-país (já compatível)

A estrutura de LGPD (papéis operador/controlador, base legal documentada, ROPA, DPA, anonimização do benchmark) é desenhada de forma que **trocar a lei aplicável por país seja configuração**, não rewrite (ex.: LFPDPPP no México). (Ver [seguranca-lgpd.md](./seguranca-lgpd.md) §12.)

## 5. Gate de ativação

Nada disto vira construção até **G3** (ver [roadmap.md](./roadmap.md)): tração comprovada + decisão de capital + 1 cliente LATAM identificado. Até lá, são apenas **colunas, interfaces e contratos** que ficam prontos — custo marginal hoje, rewrite evitado amanhã.

## 6. Resumo

| Abstração feita agora | Ativação no foguete |
|-----------------------|---------------------|
| `country_code`/`currency`/`tax_regime` no schema | popular com novos países |
| `SourceConnector` plugável | conector do ERP local |
| `PricePackage` por vertical+país | pacote de preço local |
| Feed de integridade abstraído | feed de sanções local |
| Parser fiscal abstraído | parser CFDI/DIAN/etc. |
| LGPD por papéis + base legal | lei local por configuração |
