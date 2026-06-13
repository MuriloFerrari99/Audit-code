"""App FastAPI mínimo (T-027). Endpoints de saúde e wiring inicial."""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request

from app.core.config import get_settings
from app.core.db import db_healthy
from app.core.logging import configure_logging, get_logger, request_id_var

settings = get_settings()
configure_logging(settings.log_level)
log = get_logger("api")

app = FastAPI(title="Auditoria de Gastos — API", version="0.1.0")


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex
    token = request_id_var.set(rid)
    try:
        response = await call_next(request)
    finally:
        request_id_var.reset(token)
    response.headers["x-request-id"] = rid
    return response


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: o processo está de pé."""
    return {"status": "ok", "env": settings.app_env}


@app.get("/readyz")
def readyz() -> dict[str, object]:
    """Readiness: dependências essenciais respondem."""
    ok_db = db_healthy()
    return {"status": "ok" if ok_db else "degraded", "db": ok_db}
