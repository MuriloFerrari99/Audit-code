"""Agente de onboarding (docs/onboarding-ux.md).

Responde dúvidas do usuário ao conectar o Sienge, FUNDAMENTADO numa base de
conhecimento curada (não alucina). Com chave de LLM, responde em linguagem
natural restrito à base; sem chave, cai para a FAQ estática.
"""

from __future__ import annotations

from app.agents.llm import LLMClient

KB = """
BASE DE CONHECIMENTO — Onboarding Sienge (somente leitura).

[Como gerar o usuário de API do Sienge]
1. No Sienge, acesse a área de Integrações/API (Configurações).
2. Crie um "usuário de API" com permissão SOMENTE LEITURA aos módulos de compras,
   notas, contas a pagar e orçamento.
3. Anote: subdomínio (parte do seu endereço, ex.: SUAEMPRESA em
   https://SUAEMPRESA.sienge.com.br), usuário de API e senha de API.
Esses três campos vão no formulário seguro de conexão (nunca no chat).

[O que lemos]
Pedidos de compra e itens, cotações, notas/atendimentos, contas a pagar (títulos)
e orçamento (custos unitários). Só para auditar gasto — nada mais.

[É seguro? Escrevemos algo no Sienge?]
Não escrevemos NADA no seu ERP. Todo acesso é somente leitura (apenas consultas).
A credencial é guardada criptografada e isolada por empresa.

[LGPD / privacidade]
Tratamos o dado como operador, sob seu contrato; isolamento rígido entre clientes;
você pode revogar o acesso a qualquer momento trocando a senha de API no Sienge.

[O que recebo no fim]
Uma auditoria gerencial: onde você está acima do mercado (sobrepreço), compras sem
concorrência, divergências pedido↔pagamento e estouro de quantidade — com a
evidência e o valor em R$. É consultivo: você decide o que fazer.
"""

_SYSTEM = (
    "Você é o assistente de onboarding de uma plataforma de auditoria gerencial de "
    "gastos. Responda em português, curto e tranquilizador, USANDO SOMENTE a base de "
    "conhecimento fornecida. Se a resposta não estiver na base, diga que o suporte "
    "humano ajuda. Nunca peça a senha no chat. Nunca invente."
)


def answer(question: str, tenant_id: str = "anon", llm: LLMClient | None = None) -> dict:
    if llm is not None:
        resp = llm.complete(
            f"BASE:\n{KB}\n\nPERGUNTA DO USUÁRIO: {question}",
            tenant_id=tenant_id,
            task="cheap",
            max_tokens=400,
            system=_SYSTEM,
        )
        if resp:
            return {"answer": resp, "grounded": True}
    # fallback estático: devolve a base (sempre útil, nunca alucinado)
    return {"answer": KB.strip(), "grounded": True, "fallback": True}
