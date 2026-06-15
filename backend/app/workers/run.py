"""Worker de auditoria contínua (A-2). APScheduler dispara o sync incremental +
reavaliação de regras por tenant, em intervalo configurável.

Roda no container. Audita continuamente os tenants que já têm credencial Sienge;
nunca falha em silêncio (erros vão para log + dead_letter na carga).
"""

from __future__ import annotations

import contextlib
import os

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy import text

from app.core.db import admin_session, tenant_session
from app.core.logging import configure_logging, get_logger
from app.core.secrets import get_secret_provider

log = get_logger("worker")
INTERVAL_MIN = int(os.environ.get("SYNC_INTERVAL_MIN", "60"))
MAX_ORDERS = int(os.environ.get("SYNC_MAX_ORDERS", "300"))


def _active_tenants_with_creds() -> list[str]:
    secrets = get_secret_provider()
    with admin_session() as s:
        ids = [str(r[0]) for r in s.execute(text("SELECT id FROM tenant WHERE status = 'active'"))]
    return [t for t in ids if secrets.get_optional(f"tenant/{t}/sienge/subdomain")]


def sync_active_tenants() -> None:
    # imports tardios (evitam custo no boot do worker)
    from app.connectors.sienge.connector import SiengeConnector
    from app.connectors.sienge.load import load_canonical
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

    tenants = _active_tenants_with_creds()
    log.info("worker.cycle.start", tenants=len(tenants))
    for tid in tenants:
        try:
            conn = SiengeConnector(tid, get_secret_provider(), use_fixtures=False)
            load_canonical(conn, tid, max_orders=MAX_ORDERS)
            with tenant_session(tid) as s:
                refresh_for_tenant(s, tid, limit=50)
            with tenant_session(tid) as s:
                found = run_all(s, tid)
            log.info("worker.tenant.done", tenant_id=tid, found=found)
        except Exception as e:  # um tenant não derruba os outros
            log.error("worker.tenant.error", tenant_id=tid, error=str(e))


def drain_squad_events(interval_each: int = 50) -> None:
    """Event-driven: drena o outbox de auditoria (uploads) por tenant ativo."""
    from app.agents.squad.events import drain_audit_outbox

    with admin_session() as s:
        ids = [str(r[0]) for r in s.execute(text("SELECT id FROM tenant WHERE status = 'active'"))]
    for tid in ids:
        try:
            with tenant_session(tid) as s:
                res = drain_audit_outbox(s, tid, limit=interval_each)
            if res["processed"]:
                log.info("worker.squad.drained", tenant_id=tid, **{k: res[k] for k in ("processed",)})
        except Exception as e:
            log.error("worker.squad.error", tenant_id=tid, error=str(e))


def main() -> None:
    configure_logging()
    log.info("worker.start", interval_min=INTERVAL_MIN)
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        sync_active_tenants, "interval", minutes=INTERVAL_MIN, next_run_time=None
    )  # primeira execução no próximo tick
    # auditoria event-driven dos uploads: tick curto p/ baixa latência
    scheduler.add_job(drain_squad_events, "interval", seconds=30, next_run_time=None)
    scheduler.start()


if __name__ == "__main__":
    main()
