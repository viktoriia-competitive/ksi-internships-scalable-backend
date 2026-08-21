"""Backward-compatible names for the Linux deadline adapter."""

from execution_engine.platform.linux.deadline import DeadlineGuard, compute_wall_deadline_ms

WallWatchdog = DeadlineGuard


def wall_deadline_ms(time_limit_ms: int, wall_factor: float = 2.0) -> int:
    return compute_wall_deadline_ms(time_limit_ms, wall_factor)
