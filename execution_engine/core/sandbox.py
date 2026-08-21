from __future__ import annotations

import os
import signal
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from execution_engine.core.models import ExecutionLimits
from execution_engine.platform.linux.cgroups import CgroupLease, LinuxCgroupV2
from execution_engine.platform.linux.deadline import DeadlineGuard
from execution_engine.platform.linux.launcher import LaunchRequest, ProcessLauncher
from execution_engine.platform.linux.resources import LinuxProcessObserver


@dataclass(frozen=True, slots=True)
class SandboxRequest:
    execution_id: str
    work_dir: Path
    argv: Sequence[str]
    stdin_path: Path
    stdout_path: Path
    stderr_path: Path
    limits: ExecutionLimits


@dataclass(frozen=True, slots=True)
class SandboxResult:
    exit_code: int | None
    signal: int | None
    cpu_ms: int
    wall_ms: int
    mem_kb: int
    killed_by_wall: bool
    killed_by_oom: bool
    memory_limit_enforced: bool = True
    cpu_limit_enforced: bool = True


class SandboxProvider(Protocol):
    def execute(self, request: SandboxRequest) -> SandboxResult: ...


class ProcessSandbox:
    """Linux process-backed sandbox provider assembled from host adapters."""

    _DEVELOPMENT_WALL_FLOOR_MS = 5_000

    def __init__(
        self,
        *,
        use_cgroup: bool = True,
        launcher: ProcessLauncher | None = None,
        observer: LinuxProcessObserver | None = None,
        cgroups: LinuxCgroupV2 | None = None,
    ) -> None:
        self.use_cgroup = use_cgroup
        self._launcher = launcher or ProcessLauncher()
        self._observer = observer or LinuxProcessObserver()
        self._cgroups = cgroups or LinuxCgroupV2()

    def execute(self, request: SandboxRequest) -> SandboxResult:
        lease = self._allocate_cgroup(request) if self.use_cgroup else None
        enforcement_active = lease is not None
        deadline = DeadlineGuard(self._wall_deadline(request.limits, enforcement_active))
        process = None

        try:
            started_at = time.monotonic()
            process = self._launcher.launch(
                LaunchRequest(
                    work_dir=request.work_dir,
                    run_argv=request.argv,
                    stdin_path=request.stdin_path,
                    stdout_path=request.stdout_path,
                    stderr_path=request.stderr_path,
                )
            )

            if lease is not None:
                try:
                    self._cgroups.attach(lease, process.pid)
                except OSError:
                    enforcement_active = False

            deadline.arm(process.pid)
            observation = self._observer.observe(
                process.pid,
                started_at=started_at,
                cgroup_dir=lease.path if enforcement_active and lease is not None else None,
                wall_expired=lambda: deadline.fired,
            )
            process.returncode = observation.exit_code if observation.exit_code is not None else -1
            return SandboxResult(
                exit_code=observation.exit_code,
                signal=observation.signal,
                cpu_ms=observation.cpu_ms,
                wall_ms=observation.wall_ms,
                mem_kb=observation.mem_kb,
                killed_by_wall=observation.killed_by_wall,
                killed_by_oom=observation.killed_by_oom,
                memory_limit_enforced=enforcement_active,
                cpu_limit_enforced=enforcement_active,
            )
        except Exception:
            if process is not None and process.poll() is None:
                self._kill_process_group(process.pid)
            raise
        finally:
            deadline.cancel()
            if lease is not None:
                self._release_cgroup(lease)

    def _allocate_cgroup(self, request: SandboxRequest) -> CgroupLease | None:
        try:
            return self._cgroups.allocate(
                request.execution_id,
                memory_limit_mb=request.limits.memory_limit_mb,
                pids_max=request.limits.pids_max,
            )
        except Exception:
            return None

    def _release_cgroup(self, lease: CgroupLease) -> None:
        try:
            self._cgroups.release(lease)
        except Exception:
            pass

    @classmethod
    def _wall_deadline(cls, limits: ExecutionLimits, enforcement_active: bool) -> int:
        configured = limits.wall_deadline_ms
        if enforcement_active:
            return configured
        return max(configured, cls._DEVELOPMENT_WALL_FLOOR_MS)

    @staticmethod
    def _kill_process_group(pid: int) -> None:
        try:
            os.killpg(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
