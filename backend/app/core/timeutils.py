"""Padrão de tempo (T-024, ADR-05).

Armazenar SEMPRE em UTC (timestamptz). Janelas de regra e período mensal são
calculados na timezone de negócio (America/Sao_Paulo por padrão).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def business_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().business_timezone)


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


def to_utc(dt: datetime) -> datetime:
    """Normaliza qualquer datetime para UTC. Naive é assumido como tz de negócio."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=business_tz())
    return dt.astimezone(UTC)


def to_business(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(business_tz())


def period_key(dt: datetime) -> str:
    """Chave de período mensal (YYYY-MM) na tz de negócio — usada no ledger."""
    return to_business(dt).strftime("%Y-%m")


def window_contains(reference: datetime, candidate: datetime, days: int) -> bool:
    """True se `candidate` está dentro de `days` ANTES de `reference` (janela de
    regras como fracionamento)."""
    ref = to_utc(reference)
    cand = to_utc(candidate)
    return (ref - timedelta(days=days)) <= cand <= ref
