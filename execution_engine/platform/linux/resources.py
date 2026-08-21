from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ProcessObservation:
    cpu_ms: int
    wall_ms: int
    mem_kb: int
    exit_code: int | None
    signal: int | None = None
    killed_by_wall: bool = False
    killed_by_oom: bool = False


class LinuxProcessObserver:
    """Reap one child with wait4 and translate kernel accounting into judge units."""

    def observe(
        self,
        pid: int,
        *,
        started_at: float,
        cgroup_dir: str | Path | None = None,
        wall_expired: Callable[[], bool] | None = None,
        killed_by_wall: bool = False,
    ) -> ProcessObservation:
        if not hasattr(os, "wait4"):
            raise RuntimeError("judge process accounting requires Linux/WSL os.wait4")

        _reaped_pid, wait_status, usage = os.wait4(pid, 0)
        cpu_ms = round((usage.ru_utime + usage.ru_stime) * 1000)
        wall_ms = max(0, round((time.monotonic() - started_at) * 1000))
        exit_code, termination_signal = self._decode_wait_status(wait_status)

        memory_kb = int(usage.ru_maxrss)
        if cgroup_dir is not None:
            cgroup_peak = read_memory_peak_kb(cgroup_dir)
            if cgroup_peak is not None:
                memory_kb = cgroup_peak

        if wall_expired is not None:
            try:
                killed_by_wall = killed_by_wall or bool(wall_expired())
            except Exception:
                pass

        return ProcessObservation(
            cpu_ms=int(cpu_ms),
            wall_ms=int(wall_ms),
            mem_kb=memory_kb,
            exit_code=exit_code,
            signal=termination_signal,
            killed_by_wall=killed_by_wall,
            killed_by_oom=False,
        )

    @staticmethod
    def _decode_wait_status(status: int) -> tuple[int | None, int | None]:
        if os.WIFEXITED(status):
            return os.WEXITSTATUS(status), None
        if os.WIFSIGNALED(status):
            sig = os.WTERMSIG(status)
            return -sig, sig
        return None, None


def read_memory_peak_kb(cgroup_dir: str | Path) -> int | None:
    try:
        raw = (Path(cgroup_dir) / "memory.peak").read_text(encoding="utf-8").strip()
        return int(raw) // 1024
    except (OSError, ValueError):
        return None
