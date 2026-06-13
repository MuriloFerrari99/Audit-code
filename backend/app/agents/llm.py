"""Cliente LLM com guardrails (ADR-12, agentes.md).

- Segredo via SecretProvider; SEM chave -> modo desabilitado (agentes caem no
  fallback determinístico, o sistema continua funcionando).
- Roteamento de modelo: 'strong' (Investigador/Narrador) vs 'cheap' (volume).
- Orçamento de tokens por tenant (in-process; trocável por Redis).
- Redação de PII no prompt (CPF) — minimização.
- Read-only: nenhuma tool de escrita é exposta aos agentes.
"""

from __future__ import annotations

import re

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.secrets import SecretProvider

log = get_logger("agents.llm")

_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")


def redact_pii(text: str) -> str:
    return _CPF.sub("[CPF-REDIGIDO]", text)


class LLMClient:
    def __init__(self, secrets: SecretProvider):
        self._settings = get_settings()
        self._api_key = secrets.get_optional("llm/anthropic/api_key")
        self.enabled = bool(self._api_key)
        self._spent: dict[str, int] = {}
        self._client = None
        if self.enabled:
            try:
                from anthropic import Anthropic  # noqa: PLC0415

                self._client = Anthropic(api_key=self._api_key)
            except Exception as e:  # pragma: no cover
                log.warning("agents.llm.init_failed", error=str(e))
                self.enabled = False

    def _model(self, task: str) -> str:
        return self._settings.llm_model_strong if task == "strong" else self._settings.llm_model_cheap

    def _budget_ok(self, tenant_id: str, want: int) -> bool:
        spent = self._spent.get(tenant_id, 0)
        return spent + want <= self._settings.llm_tenant_token_budget

    def complete(self, prompt: str, *, tenant_id: str, task: str = "cheap",
                 max_tokens: int = 1024, system: str | None = None) -> str | None:
        """Retorna o texto do modelo, ou None se desabilitado/estourou orçamento
        (o chamador deve ter um fallback determinístico)."""
        if not self.enabled or self._client is None:
            return None
        if not self._budget_ok(tenant_id, max_tokens):
            log.warning("agents.llm.budget_exceeded", tenant_id=tenant_id)
            return None
        safe_prompt = redact_pii(prompt)
        resp = self._client.messages.create(
            model=self._model(task),
            max_tokens=max_tokens,
            system=system or "Você é um analista de auditoria de gastos. Seja objetivo e cite a evidência. Você NÃO executa ações; apenas analisa e reporta.",
            messages=[{"role": "user", "content": safe_prompt}],
        )
        usage = getattr(resp, "usage", None)
        used = (getattr(usage, "input_tokens", 0) + getattr(usage, "output_tokens", 0)) if usage else max_tokens
        self._spent[tenant_id] = self._spent.get(tenant_id, 0) + used
        return "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
