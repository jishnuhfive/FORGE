"""Minimal identity records. Timestamps are UTC Unix seconds on every DB dialect."""

import time
import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> int:
    return int(time.time())


def identifier() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("onshape_user_id", "stack"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    onshape_user_id: Mapped[str] = mapped_column(String(128))
    stack: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[int] = mapped_column(BigInteger, default=now)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=now)
    last_login_at: Mapped[int] = mapped_column(BigInteger, default=now)


class OnshapeAuthorization(Base):
    __tablename__ = "onshape_authorizations"
    __table_args__ = (
        CheckConstraint("status IN ('connected','disconnected','revoked','error')"),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    stack: Mapped[str] = mapped_column(String(255))
    company_id: Mapped[str | None] = mapped_column(String(24))
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text)
    access_expires_at: Mapped[int | None] = mapped_column(BigInteger)
    granted_scope: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(20), default="connected")
    generation: Mapped[str] = mapped_column(String(36), default=identifier)
    retry_after: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[int] = mapped_column(BigInteger, default=now)
    updated_at: Mapped[int] = mapped_column(BigInteger, default=now)
    verified_at: Mapped[int | None] = mapped_column(BigInteger)
    disconnected_at: Mapped[int | None] = mapped_column(BigInteger)


class Session(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[int] = mapped_column(BigInteger, default=now)
    expires_at: Mapped[int] = mapped_column(BigInteger, index=True)
    last_seen_at: Mapped[int] = mapped_column(BigInteger, default=now)
    revoked_at: Mapped[int | None] = mapped_column(BigInteger)


class UserPreferences(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        CheckConstraint("theme IN ('system','light','dark')"),
        CheckConstraint("units IN ('metric','imperial')"),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    theme: Mapped[str] = mapped_column(String(10), default="system")
    units: Mapped[str] = mapped_column(String(10), default="metric")


class OAuthState(Base):
    __tablename__ = "oauth_states"
    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    browser_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[int] = mapped_column(BigInteger, index=True)
    consumed_at: Mapped[int | None] = mapped_column(BigInteger)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    outcome: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[int] = mapped_column(BigInteger, default=now, index=True)


class WriteRecord(Base):
    """Short-lived candidate/proposal authority, never a CAD snapshot/history."""

    __tablename__ = "write_records"
    id: Mapped[str] = mapped_column(String(43), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    session_hash: Mapped[str] = mapped_column(String(64), index=True)
    state: Mapped[str] = mapped_column(String(24))
    digest: Mapped[str] = mapped_column(String(64))
    payload: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[int] = mapped_column(BigInteger)
    expires_at: Mapped[int] = mapped_column(BigInteger, index=True)
    purge_at: Mapped[int] = mapped_column(BigInteger, index=True)


class WriteFence(Base):
    """Durable denial. Never expires into permission; no CAD identifiers/payload."""

    __tablename__ = "write_fences"
    workspace_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    record_id: Mapped[str] = mapped_column(String(43), unique=True)
