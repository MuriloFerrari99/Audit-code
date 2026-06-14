# Plano — Módulo de Integridade de Fornecedor (Dimensão 4)

> "Eu deveria comprar dessa empresa?" Transforma auditoria de gasto em **gasto + integridade**.
> **Planejado antes de executar** para preservar integridade/confiabilidade do sistema.
> Fontes **validadas contra a API real** (2026-06-14, CNPJ de fornecedor da Alumbra).

## 1. Fontes (validadas)

| Sinal | Fonte | Chave? | Status |
|------|-------|:-----:|--------|
| Situação cadastral (ATIVA/baixada/inapta) | **BrasilAPI** `/cnpj/v1/{cnpj}` | não | ✅ testado |
| Data de abertura (empresa-laranja/recente) | BrasilAPI (`data_inicio_atividade`) | não | ✅ |
| Quadro societário / QSA (conflito) | BrasilAPI (`qsa[]`) | não | ✅ |
| **CEIS** (inidôneas/suspensas) | Portal da Transparência `/api-de-dados/ceis` | **sim (grátis)** | ⚠️ 401 sem chave |
| **CNEP** (punidas) | Portal da Transparência `/api-de-dados/cnep` | sim | idem |
| **CEPIM** (entidades impedidas) | Portal da Transparência | sim | idem |

**Decisão de fonte para sanções (CEIS/CNEP/CEPIM):** suportar **as duas vias**:
- (a) **API do Portal** com `chave-api-dados` via SecretProvider (tempo real, por CNPJ);
- (b) **Dataset aberto da CGU** (download mensal, sem chave) como **fallback** — garante o módulo funcionar mesmo sem a chave. (Decisão a confirmar — ver §8.)

## 2. Invariantes que NÃO podem ser violadas (por isso o plano)

1. **Advisory reforçado.** Dimensão que toca reputação de pessoas/empresas. Todo achado é "**sinal a investigar**", nunca "fraude/idoneidade confirmada". Sempre cita a **fonte oficial + data** consultada. Humano decide.
2. **Nunca falhar em silêncio (o ponto mais crítico de confiabilidade).** Se a fonte está fora do ar/rate-limited, o fornecedor fica **"não verificado"** — **JAMAIS** "sem sanção". Um falso "limpo" por API caída é o pior erro possível aqui. `counterparty.status ∈ {ok, indisponivel, erro}` + `checked_at`. Achado "fornecedor não verificado" é visível.
3. **Isolamento.** Dado de integridade de um CNPJ é **público e o mesmo para todos** → vive numa tabela **compartilhada `counterparty` (sem RLS)**, como o catálogo/SINAPI. O **vínculo** "este tenant comprou de X" é o achado (tenant-scoped). Nunca mistura dado de negócio entre tenants.
4. **LGPD.** O QSA contém **dado pessoal** (sócios). Base legal: **legítimo interesse** (prevenção a fraude), com teste de proporcionalidade documentado. Minimização: guardar só nome + CPF **mascarado** + qualificação; nunca expor CPF completo. Retenção e finalidade registradas.
5. **Explicabilidade + confiança.** Sanção de fonte oficial = confiança **alta**; "empresa recém-aberta" = heurística, confiança **média/baixa** → "a investigar".
6. **Read-only.** Só consultas; nada é escrito em fonte externa.

## 3. Arquitetura (encaixe no que já existe)

```
creditor (tenant, RLS)  --cnpj-->  counterparty (compartilhado, sem RLS, cache)
                                         ▲
                          [IntegrityService] consulta+cacheia (TTL),
                          BrasilAPI (Receita/QSA) + Portal/CGU (sanções),
                          retry/backoff; status=indisponivel se falhar
                                         │
                          [Regras dim.4] creditor x counterparty -> findings
                          (advisory, evidência da fonte, confidence)
```

- **`counterparty`** (novo, compartilhado): `cnpj, razao_social, situacao_cadastral, data_abertura, cnae, sancoes (jsonb: [{fonte,tipo,orgao,data,referencia}]), qsa (jsonb minimizado), status, source, checked_at`. **Sem RLS** (referência pública). TTL de revalidação (ex.: 30 dias; sanção mais curto).
- **`IntegrityService`**: `check(cnpj) -> Counterparty` (usa cache se fresco; senão consulta, cacheia; em falha marca `indisponivel`, **não** sobrescreve dado bom anterior).
- Reuso do padrão de connector resiliente (rate limit/retry) já existente.

## 4. Regras da Dimensão 4 (advisory)

| Regra | Dispara | Severidade | Confiança | Evidência |
|------|---------|-----------|-----------|-----------|
| **I1 Fornecedor sancionado** | CNPJ em CEIS/CNEP/CEPIM | crítica | alta | registro da sanção (órgão, tipo, vigência) |
| **I2 CNPJ não-ativo** | situação ≠ ATIVA | alta | alta | situação + data |
| **I3 Empresa recém-aberta de alto valor** | abertura < N meses **e** compra > R$ X | média | média | data abertura + total comprado |
| **I4 Conflito de interesse** | sócio do fornecedor = comprador/aprovador, ou sócio comum entre concorrentes | alta | média | CNPJs/sócios em comum (mascarado) |
| **I5 Fornecedor não verificado** | sem consulta bem-sucedida | info | — | motivo (fonte indisponível) |

**Ressalva I4:** o `buyerId` do Sienge é um login, não CPF → cruzar comprador↔sócio exige dado de RH (CPF do comprador). **Fase A:** sócio-comum entre fornecedores que concorrem no mesmo pedido (factível só com QSA). **Fase B:** comprador↔sócio quando houver o cadastro de pessoas.

## 5. Confiabilidade e desempenho

- **Cache agressivo** (CNPJ muda devagar): só reconsulta após TTL. ~milhares de fornecedores → consulta sob demanda + job de revalidação em background.
- **Rate limit** das APIs públicas (BrasilAPI/Portal): limitador + backoff; fila de verificação assíncrona (não bloqueia auditoria).
- **Degradação graciosa:** uma fonte fora não derruba as outras; status por fonte.
- **Idempotência:** `counterparty` por CNPJ; revalidação atualiza, versiona sanções.

## 6. Como preserva integridade/confiabilidade do sistema

- Não toca isolamento (tabela compartilhada só com dado público; achados tenant-scoped).
- Não introduz falha silenciosa (status "não verificado" explícito).
- Mantém explicabilidade (fonte + data em toda evidência) e confiança (Módulo B).
- LGPD tratada (minimização do QSA, base legal, mascaramento).
- Testes: parser de cada fonte contra payload real (como fiz no Sienge); teste de "fonte indisponível → não verificado, nunca limpo".

## 7. Rollout (incremental, verificável)

1. `counterparty` model + migração; `IntegrityService` (BrasilAPI primeiro — sem chave).
2. Parser BrasilAPI testado contra payload real; cache + status.
3. Regras I2/I3 (situação + recém-aberta) — só BrasilAPI, já entregam valor.
4. Sanções (CEIS/CNEP) — quando a chave (ou dataset) estiver disponível → I1.
5. I4 fase A (sócio comum) com QSA.
6. UI: aba "Integridade do fornecedor" + selo no dossiê.

## 8. Decisões para você (antes de eu executar)

- **Q-A — Sanções:** registramos a **chave gratuita do Portal da Transparência** (você cadastra um e-mail e me passa a chave, via `.env`) **ou** começo só com **Receita/BrasilAPI** (situação + recém-aberta + QSA) e deixo CEIS/CNEP para quando a chave existir? *(Recomendo: começar com BrasilAPI agora — entrega I2/I3/I4 sem atrito — e ligar CEIS/CNEP quando você cadastrar a chave.)*
- **Q-B — Limiares I3:** "recém-aberta" = abertura < **12 meses** e compra > **R$ 50 mil**? (defaults; calibráveis por tenant)
- **Q-C — Conflito (I4):** começar pela **Fase A** (sócio comum entre fornecedores), já que não temos CPF dos compradores?
