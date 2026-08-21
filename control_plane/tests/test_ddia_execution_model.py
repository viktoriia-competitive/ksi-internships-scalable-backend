from __future__ import annotations

from datetime import datetime, timezone

from control_plane.runtime.core.evaluation_command import EvaluationCommand
from control_plane.runtime.core.lifecycle import (
    EXECUTION_CLAIMED,
    EXECUTION_COMPLETED,
    EXECUTION_REQUESTED,
    EXECUTION_RETRYABLE_FAILURE,
    LifecycleEvent,
    AttemptProjection,
    evolve,
)


def event(sequence: int, kind: str, payload: dict | None = None, *, run_key: str = "exec-1"):
    return LifecycleEvent(
        attempt_key="00000000-0000-0000-0000-000000000001",
        run_key=run_key,
        delivery_key="cmd-1",
        sequence=sequence,
        event_type=kind,
        payload=payload or {},
        occurred_at=datetime(2026, 1, 1, 12, sequence, tzinfo=timezone.utc),
    )


def test_projection_is_derived_by_replaying_execution_facts() -> None:
    state = AttemptProjection(attempt_key="00000000-0000-0000-0000-000000000001")
    state = evolve(state, event(1, EXECUTION_REQUESTED, {"retryIndex": 0}))
    state = evolve(state, event(2, EXECUTION_CLAIMED, {"retryIndex": 0}))
    state = evolve(
        state,
        event(
            3,
            EXECUTION_COMPLETED,
            {"verdict": "ACCEPTED", "report": {"testsPassed": 4, "testsTotal": 4}},
        ),
    )

    assert state.phase == "ACCEPTED"
    assert state.verdict == "ACCEPTED"
    assert state.report["testsPassed"] == 4
    assert state.last_sequence == 3
    assert state.started_at is not None
    assert state.finished_at is not None


def test_late_event_cannot_roll_projection_backwards() -> None:
    initial = AttemptProjection(attempt_key="s")
    completed = evolve(
        initial,
        event(5, EXECUTION_COMPLETED, {"verdict": "WRONG_ANSWER", "report": {}}),
    )
    after_late_claim = evolve(completed, event(4, EXECUTION_CLAIMED))
    assert after_late_claim == completed


def test_retry_is_a_new_execution_with_deterministic_identity() -> None:
    job = EvaluationCommand("submit:1", "s1", "p1", "Python", delivery_key="cmd-root", run_key="exec-root")
    first = job.retry()
    duplicate_retry_decision = job.retry()

    assert first == duplicate_retry_decision
    assert first.retry_index == 1
    assert first.delivery_key != job.delivery_key
    assert first.run_key != job.run_key


def test_retryable_failure_returns_projection_to_queue_without_actor_verdict() -> None:
    state = AttemptProjection(attempt_key="s")
    state = evolve(state, event(1, EXECUTION_CLAIMED, {"retryIndex": 0}))
    state = evolve(
        state,
        event(2, EXECUTION_RETRYABLE_FAILURE, {"nextRetryIndex": 1, "message": "worker lost"}),
    )
    assert state.phase == "QUEUED"
    assert state.verdict is None
    assert state.retry_index == 1
    assert state.last_infrastructure_error == "worker lost"
