from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any


ATTEMPT_OPENED = "attempt.opened"
EXECUTION_REQUESTED = "execution.requested"
EXECUTION_CLAIMED = "execution.claimed"
EXECUTION_RETRYABLE_FAILURE = "execution.retryable_failure"
EXECUTION_COMPLETED = "execution.completed"
EXECUTION_TERMINAL_FAILURE = "execution.terminal_failure"


@dataclass(frozen=True, slots=True)
class LifecycleEvent:
    attempt_key: str
    run_key: str
    delivery_key: str
    sequence: int
    event_type: str
    payload: dict[str, Any]
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class AttemptProjection:
    attempt_key: str
    phase: str = "QUEUED"
    verdict: str | None = None
    report: dict[str, Any] = field(default_factory=dict)
    retry_index: int = 0
    run_key: str | None = None
    last_sequence: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    last_infrastructure_error: str | None = None


def evolve(current: AttemptProjection, event: LifecycleEvent) -> AttemptProjection:
    """Pure projection reducer.

    The event log is authoritative. This object is disposable derived data and may
    be rebuilt by replaying events in sequence order.
    """
    if event.sequence <= current.last_sequence:
        return current

    common = {
        "run_key": event.run_key,
        "last_sequence": event.sequence,
    }

    if event.event_type in {ATTEMPT_OPENED, EXECUTION_REQUESTED}:
        return replace(
            current,
            phase="QUEUED",
            verdict=None,
            retry_index=int(event.payload.get("retryIndex", current.retry_index)),
            last_infrastructure_error=None,
            **common,
        )

    if event.event_type == EXECUTION_CLAIMED:
        return replace(
            current,
            phase="RUNNING",
            verdict=None,
            retry_index=int(event.payload.get("retryIndex", current.retry_index)),
            started_at=event.occurred_at,
            finished_at=None,
            **common,
        )

    if event.event_type == EXECUTION_RETRYABLE_FAILURE:
        return replace(
            current,
            phase="QUEUED",
            verdict=None,
            retry_index=int(event.payload.get("nextRetryIndex", current.retry_index + 1)),
            last_infrastructure_error=str(event.payload.get("message", ""))[:2000] or None,
            **common,
        )

    if event.event_type == EXECUTION_COMPLETED:
        verdict = str(event.payload.get("verdict") or "INTERNAL_ERROR")
        report = dict(event.payload.get("report") or {})
        return replace(
            current,
            phase=verdict,
            verdict=verdict,
            report=report,
            finished_at=event.occurred_at,
            last_infrastructure_error=None,
            **common,
        )

    if event.event_type == EXECUTION_TERMINAL_FAILURE:
        report = dict(event.payload.get("report") or {})
        return replace(
            current,
            phase="INTERNAL_ERROR",
            verdict="INTERNAL_ERROR",
            report=report,
            finished_at=event.occurred_at,
            last_infrastructure_error=str(event.payload.get("message", ""))[:2000] or None,
            **common,
        )

    return replace(current, **common)
