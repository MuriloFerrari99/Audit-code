"""Schemas Pydantic da API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    tenant_id: str | None = None  # obrigatório se o usuário pertence a >1 tenant


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    tenant_id: str | None = None
    role: str | None = None


class RefreshIn(BaseModel):
    refresh_token: str
    tenant_id: str | None = None


class CurrentUser(BaseModel):
    user_id: str
    email: str
    tenant_id: str | None
    role: str | None


class EvidenceOut(BaseModel):
    entity_type: str
    role: str
    snippet: str | None = None
    value: dict | None = None


class FindingOut(BaseModel):
    id: str
    rule_id: str
    severity: str
    status: str
    exposed_amount: Decimal | None = None
    confidence: Decimal | None = None
    title: str | None = None
    project_id: str | None = None
    created_at: datetime
    evidence: list[EvidenceOut] = Field(default_factory=list)


class ReviewIn(BaseModel):
    decision: str  # accept | dismiss | escalate
    reason: str | None = None


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    company_name: str


class SiengeCredsIn(BaseModel):
    subdomain: str
    user: str
    password: str


class AssistantIn(BaseModel):
    question: str
