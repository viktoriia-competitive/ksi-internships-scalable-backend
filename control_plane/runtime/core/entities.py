from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PageSlice(Generic[T]):
    entries: list[T]
    total_entries: int
    index: int
    size: int
    total_pages: int


@dataclass(frozen=True, slots=True)
class Challenge:
    key: str
    short_code: str
    name: str
    level: str
    score: int | None
    accepted_count: int
    mode: str
    labels: list[str]
    runtimes: list[str]
    budget: dict[str, Any]
    profile: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Account:
    key: uuid.UUID
    handle: str
    accepted_count: int
    completed_challenge_keys: list[str]


@dataclass(frozen=True, slots=True)
class Attempt:
    key: uuid.UUID
    account_key: uuid.UUID
    actor_handle: str
    challenge_key: str
    challenge_short_code: str
    challenge_name: str
    runtime: str
    phase: str
    artifact_ref: str
    source_text: str
    artifact_name: str
    media_type: str
    artifact_bytes: int
    report: dict[str, Any]
    work_key: str
    request_key: str | None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class NewAttempt:
    key: uuid.UUID
    account_key: uuid.UUID
    actor_handle: str
    challenge_key: str
    challenge_short_code: str
    challenge_name: str
    runtime: str
    artifact_ref: str
    source_text: str
    artifact_name: str
    media_type: str
    artifact_bytes: int
    work_key: str
    request_key: str | None
    created_at: datetime
    phase: str = "QUEUED"
    report: dict[str, Any] = field(default_factory=dict)
