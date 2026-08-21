from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from execution_engine.platform.linux.cgroups import LinuxCgroupV2


def test_cgroup_detection_is_explicit_about_host_capability() -> None:
    root = LinuxCgroupV2().detect_root()
    assert root is None or (root / "cgroup.controllers").is_file()


def test_custom_non_cgroup_root_is_not_detected(tmp_path: Path) -> None:
    assert LinuxCgroupV2(tmp_path).detect_root() is None


def test_allocate_limits_when_hierarchy_is_writable() -> None:
    manager = LinuxCgroupV2()
    root = manager.detect_root()
    if root is None:
        pytest.skip("cgroup v2 is unavailable")
    try:
        lease = manager.allocate(f"test-{uuid.uuid4().hex[:8]}", memory_limit_mb=8, pids_max=12)
    except RuntimeError as exc:
        pytest.skip(f"cgroup hierarchy is not writable: {exc}")
    try:
        assert lease.memory_max_bytes == 8 * 1024 * 1024
        assert lease.pids_max == 12
        assert lease.path.is_dir()
    finally:
        manager.release(lease)
