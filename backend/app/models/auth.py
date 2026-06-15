"""Usuários da plataforma e vínculo com tenant/escopo (ADR-08, T-050).

User é global (pode pertencer a mais de um tenant via membership). Membership
carrega papel e escopo (empresas/obras) — a app aplica escopo acima do RLS.
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, _uuid


class Role(enum.StrEnum):
    OWNER = "owner"
    CONTROLLER = "controller"
    PROCUREMENT = "procurement"
    VIEWER = "viewer"
    TENANT_ADMIN = "tenant_admin"


class User(Base, TimestampMixin):
    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # Argon2
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Membership(Base, TimestampMixin):
    __tablename__ = "membership"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_user.id"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), default=Role.VIEWER.value, nullable=False)
    # Escopo opcional (None = todas as empresas/obras do tenant):
    company_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    project_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
