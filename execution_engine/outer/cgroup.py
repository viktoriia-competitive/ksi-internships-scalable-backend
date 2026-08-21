"""Compatibility facade for the Linux cgroup-v2 adapter."""

from __future__ import annotations

from pathlib import Path

from execution_engine.platform.linux.cgroups import CgroupLease, LinuxCgroupV2

CgroupLeaf = CgroupLease
CgroupController = LinuxCgroupV2
_DEFAULT = LinuxCgroupV2()


def cgroup_v2_root() -> Path | None:
    return _DEFAULT.detect_root()


def create_leaf(
    name: str,
    *,
    memory_limit_mb: int,
    pids_max: int = 128,
    parent: Path | None = None,
) -> CgroupLeaf:
    return _DEFAULT.allocate(
        name,
        memory_limit_mb=memory_limit_mb,
        pids_max=pids_max,
        parent=parent,
    )


def add_process(leaf: CgroupLeaf, pid: int) -> None:
    _DEFAULT.attach(leaf, pid)


def kill_all(leaf: CgroupLeaf) -> None:
    _DEFAULT.terminate(leaf)


def memory_peak_kb(leaf: CgroupLeaf) -> int | None:
    return _DEFAULT.memory_peak_kb(leaf)


def remove_leaf(leaf: CgroupLeaf, *, wait_empty_s: float = 0.5) -> None:
    _DEFAULT.release(leaf, wait_empty_s=wait_empty_s)
