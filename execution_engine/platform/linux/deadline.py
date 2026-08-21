from __future__ import annotations

import os
import signal
import threading


def compute_wall_deadline_ms(time_limit_ms: int, factor: float = 2.0) -> int:
    cpu_budget = max(1, int(time_limit_ms))
    return max(cpu_budget, int(cpu_budget * factor))


class DeadlineGuard:
    """One-shot wall-clock deadline for a Unix process group."""

    def __init__(self, deadline_ms: int) -> None:
        self.deadline_ms = max(1, int(deadline_ms))
        self._timer: threading.Timer | None = None
        self._target_pgid: int | None = None
        self._fired = threading.Event()
        self._lock = threading.Lock()

    def arm(self, pgid: int) -> None:
        with self._lock:
            self._cancel_locked()
            self._target_pgid = int(pgid)
            self._fired.clear()
            timer = threading.Timer(self.deadline_ms / 1000.0, self._expire)
            timer.daemon = True
            self._timer = timer
            timer.start()

    def cancel(self) -> None:
        with self._lock:
            self._cancel_locked()

    @property
    def fired(self) -> bool:
        return self._fired.is_set()

    def _cancel_locked(self) -> None:
        timer, self._timer = self._timer, None
        if timer is not None:
            timer.cancel()

    def _expire(self) -> None:
        self._fired.set()
        pgid = self._target_pgid
        if pgid is None:
            return
        try:
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            return
