from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AccountRow(Base):
    __tablename__ = "accounts"

    key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    handle: Mapped[str] = mapped_column(String(64), nullable=False)
    handle_normalized: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    accepted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_challenge_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    attempts: Mapped[list["AttemptRow"]] = relationship(back_populates="account")


class ChallengeRow(Base):
    __tablename__ = "challenges"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    short_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False, default="easy")
    score: Mapped[int | None] = mapped_column(Integer)
    accepted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="stdio")
    labels: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    runtimes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    budget: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_challenge_discovery_level", "level", "accepted_count"),
        Index("ix_challenge_discovery_mode", "mode", "short_code"),
        Index("ix_challenge_labels_gin", "labels", postgresql_using="gin"),
    )


class AttemptRow(Base):
    __tablename__ = "attempts"

    key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_key: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.key"), nullable=False)
    actor_handle: Mapped[str] = mapped_column(String(64), nullable=False)
    challenge_key: Mapped[str] = mapped_column(ForeignKey("challenges.key"), nullable=False)
    challenge_short_code: Mapped[str] = mapped_column(String(128), nullable=False)
    challenge_name: Mapped[str] = mapped_column(String(512), nullable=False)
    runtime: Mapped[str] = mapped_column(String(32), nullable=False)
    phase: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    artifact_ref: Mapped[str] = mapped_column(Text, nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    artifact_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    work_key: Mapped[str] = mapped_column(String(160), nullable=False)
    request_key: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    account: Mapped[AccountRow] = relationship(back_populates="attempts")

    __table_args__ = (
        UniqueConstraint("work_key", name="uq_attempt_work_key"),
        UniqueConstraint("account_key", "request_key", name="uq_attempt_actor_request"),
        Index("ix_attempt_actor_created", "account_key", "created_at"),
        Index("ix_attempt_challenge_created", "challenge_key", "created_at"),
        Index("ix_attempt_phase_created", "phase", "created_at"),
    )


class CommandOutboxRow(Base):
    __tablename__ = "control_outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    aggregate_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_control_outbox_pending", "published", "id"),)


class ChallengeRevisionRow(Base):
    __tablename__ = "challenge_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    challenge_key: Mapped[str] = mapped_column(ForeignKey("challenges.key"), nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    bundle_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_ref: Mapped[str] = mapped_column(Text, nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("challenge_key", "revision", name="uq_challenge_revision_number"),
        UniqueConstraint("challenge_key", "bundle_digest", name="uq_challenge_revision_digest"),
        Index("ix_challenge_revision_latest", "challenge_key", "revision"),
    )


class LifecycleEventRow(Base):
    __tablename__ = "lifecycle_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_key: Mapped[uuid.UUID] = mapped_column(ForeignKey("attempts.key"), nullable=False, index=True)
    run_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    delivery_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(180), nullable=False, unique=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("attempt_key", "sequence", name="uq_lifecycle_attempt_sequence"),
        Index("ix_lifecycle_attempt_time", "attempt_key", "sequence"),
    )


class AttemptProjectionRow(Base):
    __tablename__ = "attempt_projections"

    attempt_key: Mapped[uuid.UUID] = mapped_column(ForeignKey("attempts.key"), primary_key=True)
    phase: Mapped[str] = mapped_column(String(32), nullable=False, default="QUEUED")
    verdict: Mapped[str | None] = mapped_column(String(32))
    report: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    retry_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run_key: Mapped[str | None] = mapped_column(String(64))
    last_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_infrastructure_error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (Index("ix_attempt_projection_phase", "phase", "updated_at"),)


class ProcessedCommandRow(Base):
    __tablename__ = "processed_commands"

    consumer: Mapped[str] = mapped_column(String(128), primary_key=True)
    delivery_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
