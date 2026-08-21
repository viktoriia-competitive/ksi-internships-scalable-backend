"""Compatibility facade for Linux process accounting."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from execution_engine.platform.linux.resources import LinuxProcessObserver, ProcessObservation, read_memory_peak_kb

MeasureSample = ProcessObservation
_OBSERVER = LinuxProcessObserver()


def measure_process_group(
    pid: int,
    *,
    start_monotonic: float,
    cgroup_path: str | None = None,
    killed_by_wall: bool = False,
    wall_fired: Callable[[], bool] | None = None,
) -> MeasureSample:
    return _OBSERVER.observe(
        pid,
        started_at=start_monotonic,
        cgroup_dir=cgroup_path,
        wall_expired=wall_fired,
        killed_by_wall=killed_by_wall,
    )


def read_cgroup_memory_peak_kb(cgroup_path: str | Path) -> int | None:
    return read_memory_peak_kb(cgroup_path)
