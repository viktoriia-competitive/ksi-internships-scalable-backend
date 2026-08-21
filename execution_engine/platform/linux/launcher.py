from __future__ import annotations

import os
import shutil
import subprocess
from contextlib import ExitStack
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Sequence


class IsolationMode(str, Enum):
    NONE = "none"
    BUBBLEWRAP = "bwrap"


@dataclass(frozen=True, slots=True)
class LaunchRequest:
    work_dir: Path
    run_argv: Sequence[str]
    stdin_path: Path | None = None
    stdout_path: Path | None = None
    stderr_path: Path | None = None
    extra_ro_mounts: Sequence[Path] = field(default_factory=tuple)
    sandbox: str | None = None


@dataclass(frozen=True, slots=True)
class LaunchPlan:
    argv: list[str]
    cwd: str | None


def resolve_isolation_mode(override: str | None = None) -> IsolationMode:
    raw = (override or os.getenv("JUDGE_SANDBOX") or "none").strip().casefold()
    if raw in {"", "none", "off", "0", "false"}:
        return IsolationMode.NONE
    if raw in {"bwrap", "bubblewrap", "jail"}:
        return IsolationMode.BUBBLEWRAP
    raise ValueError(f"unsupported JUDGE_SANDBOX mode {raw!r}; expected none or bwrap")


class ProcessLauncher:
    """Build and spawn a contestant process without owning lifecycle/reaping."""

    def launch(self, request: LaunchRequest) -> subprocess.Popen:
        if not request.run_argv:
            raise ValueError("run_argv must contain at least one argument")
        plan = self.plan(request)
        work_dir = Path(request.work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        with ExitStack() as files:
            stdin = self._input(files, request.stdin_path)
            stdout = self._output(files, request.stdout_path)
            stderr = self._output(files, request.stderr_path)
            return subprocess.Popen(
                plan.argv,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                cwd=plan.cwd,
                start_new_session=True,
                close_fds=True,
            )

    def plan(self, request: LaunchRequest) -> LaunchPlan:
        mode = resolve_isolation_mode(request.sandbox)
        work_dir = Path(request.work_dir).resolve()
        if mode is IsolationMode.NONE:
            return LaunchPlan(argv=list(request.run_argv), cwd=str(work_dir))
        return LaunchPlan(argv=self._bubblewrap_argv(request, work_dir), cwd=None)

    @staticmethod
    def bubblewrap_available() -> bool:
        return shutil.which("bwrap") is not None

    def _bubblewrap_argv(self, request: LaunchRequest, work_dir: Path) -> list[str]:
        if not self.bubblewrap_available():
            raise RuntimeError("bubblewrap is unavailable; install bwrap or use JUDGE_SANDBOX=none")

        argv = [
            "bwrap",
            "--unshare-net",
            "--unshare-pid",
            "--die-with-parent",
            "--new-session",
            "--tmpfs", "/tmp",
            "--proc", "/proc",
            "--dev", "/dev",
            "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/lib", "/lib",
        ]
        for system_path in ("/lib64", "/lib32", "/bin", "/sbin"):
            if Path(system_path).exists():
                argv.extend(["--ro-bind", system_path, system_path])
        if not Path("/bin").exists() and Path("/usr/bin").exists():
            argv.extend(["--symlink", "usr/bin", "/bin"])

        argv.extend(["--bind", str(work_dir), "/box", "--chdir", "/box"])
        for mount in request.extra_ro_mounts:
            host = Path(mount).resolve()
            if host.exists():
                argv.extend(["--ro-bind", str(host), str(host)])
        argv.extend([
            "--clearenv",
            "--setenv", "PATH", "/usr/bin:/bin",
            "--setenv", "HOME", "/box",
            "--setenv", "LANG", "C.UTF-8",
            "--",
        ])
        argv.extend(self._rewrite_workdir_paths(request.run_argv, work_dir))
        return argv

    @staticmethod
    def _rewrite_workdir_paths(arguments: Sequence[str], work_dir: Path) -> list[str]:
        rewritten: list[str] = []
        for argument in arguments:
            try:
                candidate = Path(argument)
                if candidate.is_absolute():
                    relative = candidate.resolve().relative_to(work_dir)
                    rewritten.append(f"/box/{relative.as_posix()}")
                    continue
            except (OSError, RuntimeError, ValueError):
                pass
            rewritten.append(argument)
        return rewritten

    @staticmethod
    def _input(stack: ExitStack, path: Path | None):
        if path is None:
            return subprocess.DEVNULL
        return stack.enter_context(open(path, "rb"))

    @staticmethod
    def _output(stack: ExitStack, path: Path | None):
        if path is None:
            return subprocess.DEVNULL
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        return stack.enter_context(open(path, "wb"))
