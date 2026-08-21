from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChallengeQuery:
    search: str = ""
    level: str = "all"
    label: str = "all"
    mode: str = "all"
    order_by: str = "shortCode"
    direction: str = "asc"
    index: int = 1
    size: int = 50


@dataclass(frozen=True, slots=True)
class AttemptQuery:
    index: int = 1
    size: int = 50
    challenge_key: str | None = None
    phase: str | None = None
    actor_key: str | None = None


@dataclass(frozen=True, slots=True)
class OpenAttemptCommand:
    challenge_key: str
    runtime: str
    source_text: str
    artifact_name: str | None = None
    media_type: str | None = None
