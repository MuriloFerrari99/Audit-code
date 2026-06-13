"""Contrato de regra, contexto, rascunho de achado e registry (ADR-03/07).

Uma Rule é determinística: dado o mesmo dado + config, produz os mesmos
FindingDraft. O engine cuida de persistência, dedup e ciclo de vida.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.money import Money
from app.models.findings import Severity


def dedup_key(rule_id: str, *parts: object) -> str:
    raw = "|".join([rule_id, *[str(p) for p in parts]])
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


@dataclass
class EvidenceDraft:
    entity_type: str
    role: str
    entity_id: str | None = None
    snippet: str | None = None
    value: dict | None = None


@dataclass
class FindingDraft:
    rule_id: str
    rule_version: int
    dedup_key: str
    severity: str
    exposed_amount: Money | None
    title: str
    project_id: str | None = None
    evidence: list[EvidenceDraft] = field(default_factory=list)
    reference_snapshot: dict | None = None
    config_snapshot: dict | None = None


@dataclass
class RuleContext:
    tenant_id: str
    params: dict
    now: datetime


class Rule(Protocol):
    id: str
    version: int
    dimension: int
    severity_default: Severity
    default_params: dict

    def evaluate(self, session: Session, ctx: RuleContext) -> list[FindingDraft]: ...


# --- Registry ---------------------------------------------------------------

_REGISTRY: dict[str, Rule] = {}


def register(rule: Rule) -> Rule:
    if rule.id in _REGISTRY:
        raise ValueError(f"regra duplicada: {rule.id}")
    _REGISTRY[rule.id] = rule
    return rule


class _Registry:
    def all(self) -> list[Rule]:
        return list(_REGISTRY.values())

    def get(self, rule_id: str) -> Rule:
        return _REGISTRY[rule_id]

    def ids(self) -> list[str]:
        return list(_REGISTRY.keys())


registry = _Registry()


def pct(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value))
