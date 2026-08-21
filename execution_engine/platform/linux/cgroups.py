from __future__ import annotations

import os
import signal
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CgroupLease:
    path: Path
    memory_max_bytes: int
    pids_max: int


class LinuxCgroupV2:
    """Filesystem-backed lifecycle manager for disposable cgroup-v2 leaves."""

    def __init__(self, root: Path | None = None, *, namespace: str = "runline") -> None:
        self._configured_root = Path(root) if root is not None else None
        self.namespace = namespace

    def detect_root(self) -> Path | None:
        root = self._configured_root or Path("/sys/fs/cgroup")
        if root.is_dir() and (root / "cgroup.controllers").is_file():
            return root
        return None

    def allocate(
        self,
        name: str,
        *,
        memory_limit_mb: int,
        pids_max: int = 128,
        parent: Path | None = None,
    ) -> CgroupLease:
        root = self.detect_root()
        if root is None:
            raise RuntimeError("cgroup v2 unified hierarchy is not available")
        base = Path(parent) if parent is not None else root / self.namespace
        try:
            base.mkdir(parents=True, exist_ok=True)
            self._request_controllers(root)
            self._request_controllers(base)
        except OSError as exc:
            raise RuntimeError(f"cannot prepare cgroup hierarchy at {base}: {exc}") from exc

        leaf = base / self._sanitize(name)
        try:
            leaf.mkdir()
        except FileExistsError as exc:
            raise RuntimeError(f"cgroup leaf already exists: {leaf}") from exc
        except OSError as exc:
            raise RuntimeError(f"cannot create cgroup leaf {leaf}: {exc}") from exc

        memory_bytes = max(1, int(memory_limit_mb)) * 1024 * 1024
        processes = max(1, int(pids_max))
        try:
            self._write(leaf / "memory.max", memory_bytes)
            self._write(leaf / "pids.max", processes)
        except OSError as exc:
            try:
                leaf.rmdir()
            except OSError:
                pass
            raise RuntimeError(f"cannot apply cgroup limits at {leaf}: {exc}") from exc
        return CgroupLease(leaf, memory_bytes, processes)

    def attach(self, lease: CgroupLease, pid: int) -> None:
        self._write(lease.path / "cgroup.procs", int(pid))

    def memory_peak_kb(self, lease: CgroupLease) -> int | None:
        try:
            return int((lease.path / "memory.peak").read_text(encoding="utf-8").strip()) // 1024
        except (OSError, ValueError):
            return None

    def terminate(self, lease: CgroupLease) -> None:
        kernel_kill = lease.path / "cgroup.kill"
        if kernel_kill.is_file():
            try:
                self._write(kernel_kill, 1)
                return
            except OSError:
                pass
        for pid in self._members(lease):
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

    def release(self, lease: CgroupLease, *, wait_empty_s: float = 0.5) -> None:
        self.terminate(lease)
        deadline = time.monotonic() + max(0.0, wait_empty_s)
        while time.monotonic() < deadline and self._members(lease):
            time.sleep(0.01)
            self.terminate(lease)
        try:
            lease.path.rmdir()
        except OSError as exc:
            self.terminate(lease)
            time.sleep(0.05)
            try:
                lease.path.rmdir()
            except OSError:
                raise RuntimeError(f"cannot remove cgroup leaf {lease.path}: {exc}") from exc

    @staticmethod
    def _sanitize(name: str) -> str:
        return name.replace("..", "_").replace("/", "_").strip() or "job"

    @staticmethod
    def _write(path: Path, value: int | str) -> None:
        path.write_text(f"{value}\n", encoding="utf-8")

    @staticmethod
    def _members(lease: CgroupLease) -> list[int]:
        try:
            lines = (lease.path / "cgroup.procs").read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        members: list[int] = []
        for line in lines:
            try:
                members.append(int(line.strip()))
            except ValueError:
                pass
        return members

    @staticmethod
    def _request_controllers(directory: Path) -> None:
        control = directory / "cgroup.subtree_control"
        if not control.is_file():
            return
        try:
            enabled = set(control.read_text(encoding="utf-8").split())
            missing = [f"+{name}" for name in ("memory", "pids") if name not in enabled]
            if missing:
                control.write_text(" ".join(missing) + "\n", encoding="utf-8")
        except OSError:
            pass
