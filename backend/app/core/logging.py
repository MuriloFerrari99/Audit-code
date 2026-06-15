"""Logging estruturado (T-025, ADR-18).

JSON via structlog, com request_id e tenant_id em contextvars. Nunca logar PII
sensível nem segredos.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar

import structlog

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)


def _inject_context(_logger, _method, event_dict):
    rid = request_id_var.get()
    tid = tenant_id_var.get()
    if rid:
        event_dict["request_id"] = rid
    if tid:
        event_dict["tenant_id"] = tid
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _inject_context,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "app") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
