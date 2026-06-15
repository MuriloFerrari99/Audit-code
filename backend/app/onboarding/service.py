"""Serviço de onboarding self-serve (docs/onboarding-ux.md).

- probe_sienge: validação AO VIVO, read-only (derruba o atrito "será que conectou?").
- connect: persiste a credencial CRIPTOGRAFADA por tenant.
- start_run/get_status: dispara a 1ª auditoria em background e expõe progresso.

A 1ª auditoria roda em thread (worker/fila entram depois). Read-only no Sienge.
"""

from __future__ import annotations

import contextlib
import threading

import httpx

from app.core.logging import get_logger
from app.core.secrets import DbSecretProvider, get_secret_provider

log = get_logger("onboarding")

# Estado de progresso por tenant (MVP em memória; migrar p/ tabela/worker depois).
_STATUS: dict[str, dict] = {}


def probe_sienge(subdomain: str, user: str, password: str) -> dict:
    """Testa a conexão com o Sienge (somente leitura) e devolve prova de vida."""
    base = f"https://api.sienge.com.br/{subdomain}/public/api/v1"
    try:
        with httpx.Client(auth=(user, password), timeout=20) as c:
            r = c.get(f"{base}/creditors", params={"limit": 1})
            if r.status_code == 401:
                return {"ok": False, "reason": "Usuário ou senha de API inválidos (401)."}
            if r.status_code == 404:
                return {
                    "ok": False,
                    "reason": "Subdomínio não encontrado (404). Confira o endereço.",
                }
            r.raise_for_status()
            creditors = r.json().get("resultSetMetadata", {}).get("count")
            ro = c.get(f"{base}/purchase-orders", params={"limit": 1})
            orders = ro.json().get("resultSetMetadata", {}).get("count") if ro.is_success else None
    except httpx.HTTPError as e:
        return {"ok": False, "reason": f"Falha de conexão: {e}"}
    return {"ok": True, "creditors": creditors, "orders": orders}


def connect_sienge(tenant_id: str, subdomain: str, user: str, password: str) -> dict:
    """Persiste a credencial criptografada por tenant (após probe ok)."""
    db = DbSecretProvider()
    db.set(tenant_id, f"tenant/{tenant_id}/sienge/subdomain", subdomain)
    db.set(tenant_id, f"tenant/{tenant_id}/sienge/user", user)
    db.set(tenant_id, f"tenant/{tenant_id}/sienge/password", password)
    log.info("onboarding.connected", tenant_id=tenant_id, subdomain=subdomain)
    return {"ok": True}


def _run(tenant_id: str, max_orders: int) -> None:
    # imports tardios (evita custo no import do módulo)
    from app.connectors.sienge.connector import SiengeConnector
    from app.connectors.sienge.load import load_canonical
    from app.core.db import tenant_session
    from app.integrity.service import refresh_for_tenant
    from app.rules.builtin import register_builtin_rules
    from app.rules.engine import run_all
    from app.rules.fiscal_rules import register_fiscal_rules
    from app.rules.integrity_rules import register_integrity_rules
    from app.rules.payment_rules import register_payment_rules

    for reg in (
        register_builtin_rules,
        register_integrity_rules,
        register_fiscal_rules,
        register_payment_rules,
    ):
        with contextlib.suppress(ValueError):
            reg()
    try:
        _STATUS[tenant_id] = {"state": "carregando", "step": "lendo dados do Sienge"}
        connector = SiengeConnector(tenant_id, get_secret_provider(), use_fixtures=False)
        summary = load_canonical(connector, tenant_id, max_orders=max_orders)
        _STATUS[tenant_id] = {
            "state": "verificando",
            "step": "checando integridade dos fornecedores",
        }
        with tenant_session(tenant_id) as s:
            refresh_for_tenant(s, tenant_id, limit=50)
        _STATUS[tenant_id] = {"state": "auditando", "step": "rodando regras", "loaded": summary}
        with tenant_session(tenant_id) as s:
            found = run_all(s, tenant_id)
        _STATUS[tenant_id] = {
            "state": "pronto",
            "loaded": summary,
            "found": found,
            "total_findings": sum(found.values()),
        }
        log.info("onboarding.run.done", tenant_id=tenant_id, found=found)
    except Exception as e:  # nunca falhar em silêncio
        log.error("onboarding.run.error", tenant_id=tenant_id, error=str(e))
        _STATUS[tenant_id] = {"state": "erro", "reason": str(e)}


def start_run(tenant_id: str, max_orders: int = 300) -> dict:
    if _STATUS.get(tenant_id, {}).get("state") in {"carregando", "auditando"}:
        return {"state": "ja_em_andamento"}
    _STATUS[tenant_id] = {"state": "iniciando"}
    threading.Thread(target=_run, args=(tenant_id, max_orders), daemon=True).start()
    return {"state": "iniciado"}


def get_status(tenant_id: str) -> dict:
    return _STATUS.get(tenant_id, {"state": "nao_iniciado"})
