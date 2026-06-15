"""App FastAPI mínimo (T-027). Endpoints de saúde e wiring inicial."""

from __future__ import annotations

import os
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes_admin import router as admin_router
from app.api.routes_auth import router as auth_router
from app.api.routes_billing import router as billing_router
from app.api.routes_findings import router as findings_router
from app.api.routes_onboarding import router as onboarding_router
from app.api.routes_reports import router as reports_router
from app.api.routes_upload import router as upload_router
from app.core.config import get_settings
from app.core.db import db_healthy
from app.core.logging import configure_logging, get_logger, request_id_var
from app.rules.builtin import register_builtin_rules
from app.rules.fiscal_rules import register_fiscal_rules
from app.rules.integrity_rules import register_integrity_rules
from app.rules.payment_rules import register_payment_rules
from app.rules.retention_rules import register_retention_rules

settings = get_settings()
configure_logging(settings.log_level)
log = get_logger("api")

# Registra as regras no registry (idempotente por processo).
register_builtin_rules()
register_integrity_rules()
register_fiscal_rules()
register_payment_rules()
register_retention_rules()

app = FastAPI(title="Auditoria de Gastos — API", version="0.1.0")

# CORS para o frontend (origens configuráveis; default dev localhost:3000).
_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(findings_router)
app.include_router(reports_router)
app.include_router(onboarding_router)
app.include_router(upload_router)
app.include_router(billing_router)
app.include_router(admin_router)


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


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
