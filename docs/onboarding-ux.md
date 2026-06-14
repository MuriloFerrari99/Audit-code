# UX de Onboarding — Auditoria self-serve (Sienge-first)

## Princípio: time-to-value em minutos, atrito mínimo

Qualquer empresa deve conseguir, sozinha, **conectar o Sienge e ver "estou dentro ou fora do mercado e onde estão as lacunas"** sem call de vendas, sem planilha, sem TI. O onboarding é o produto.

## A jornada (4 telas + agente)

```
  [1 Criar conta]  →  [2 Conectar Sienge]  →  [3 Auditando…]  →  [4 Primeiro valor]
        e-mail            (agente ajuda)        (ao vivo)         "R$ X em N achados"
```

### 1. Criar conta (10s)
- E-mail + senha. Cria `tenant` + `company` automaticamente (provisionamento na hora).

### 2. Conectar Sienge — **o ponto crítico de atrito**
- 3 campos: **subdomínio, usuário de API, senha de API**.
- **Agente de onboarding** ao lado (chat): responde "onde gero a chave de API?", "é seguro?", "o que vocês acessam?" — fundamentado em base de conhecimento real, não alucinação.
- Botão **"Testar conexão"** → validação **ao vivo, read-only**: em 2s mostra ✓ e prova de vida ("conectado: 3.390 fornecedores, 7.206 pedidos"). Feedback instantâneo derruba a ansiedade.
- Mensagens de erro úteis (401 = credencial; 404 = subdomínio).

### 3. Auditando… (progresso ao vivo)
- "Conectado ✓ · lendo pedidos · casando cotações · auditando 6 regras".
- Roda em background; barra/percentual; sem travar a tela.

### 4. Primeiro valor (o "aha")
- Manchete: **"Encontramos R$ X em Y achados"** + **"em Z insumos você está acima do mercado"**.
- Top 5 achados com evidência e R$.
- CTA: "Ver tudo" → dashboard. "Revisar" → fluxo aceitar/descartar (gera rótulo).

## O agente de onboarding (read-only, fundamentado)
- Base de conhecimento curada: passo a passo do **usuário de API somente-leitura no Sienge**, o que lemos (pedidos, notas, títulos, orçamento, cotações), garantia read-only, LGPD/segurança.
- Sem chave de LLM → cai para a **FAQ estática** (mesma base). Nunca inventa.
- Nunca pede dado sensível no chat; credencial só vai no formulário seguro.

## Posicionamento (qualquer empresa, auditoria gerencial)
- Linguagem: "auditoria **gerencial** de gastos — está dentro ou fora do mercado?", **advisory**, humano decide. Nunca "auditoria independente".
- Referência de mercado: histórico próprio (Camada 0) + SINAPI (Camada 1) + benchmark anônimo (Camada 2, futuro).

## Atrito eliminado (decisões de design)
| Atrito comum | Como removemos |
|--------------|----------------|
| "Preciso de implantação/TI" | self-serve: conectar = 3 campos + testar |
| "Não sei se conectou" | teste ao vivo com prova de vida |
| "Onde pego a chave?" | agente de onboarding guia |
| "É seguro? o que acessam?" | agente explica + read-only provado por design |
| "Demora pra ver valor" | primeira auditoria roda na hora, manchete em R$ |
| "Config complexa" | defaults inteligentes; calibração automática depois |

## Segurança no onboarding
- Credencial do Sienge **nunca** trafega no chat; só no formulário, e é **persistida criptografada** (Fernet, chave derivada do segredo do app) por tenant — `tenant_secret`.
- Teste de conexão é **somente leitura** (GET); nada é escrito no Sienge.
- Isolamento: tudo sob o `tenant` do usuário (RLS via `app_rw`, ver auditoria C-1).

## Escopo desta entrega
- Backend: `/onboarding/test` (validação ao vivo), `/onboarding/connect` (persiste cred criptografada + provisiona), `/onboarding/run` (dispara sync+regras em background), `/onboarding/status`, `/onboarding/assistant` (agente FAQ/LLM). Signup.
- Frontend: wizard `/onboarding` + widget do agente, reusando o design system.
- Futuro: WhatsApp/e-mail de "auditoria pronta", multi-ERP, benchmark cross-cliente.
