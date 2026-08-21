from __future__ import annotations

import signal
import time
from pathlib import Path

import pytest

from execution_engine.platform.linux.deadline import DeadlineGuard, compute_wall_deadline_ms
from execution_engine.platform.linux.launcher import LaunchRequest, ProcessLauncher, resolve_isolation_mode
from execution_engine.platform.linux.resources import LinuxProcessObserver


def test_wall_deadline_never_falls_below_cpu_budget() -> None:
    assert compute_wall_deadline_ms(100, 0.5) == 100
    assert compute_wall_deadline_ms(100, 2.5) == 250
    assert compute_wall_deadline_ms(0, 2.0) >= 1


def test_isolation_mode_aliases_are_normalized() -> None:
    assert resolve_isolation_mode("off").value == "none"
    assert resolve_isolation_mode("bubblewrap").value == "bwrap"
    with pytest.raises(ValueError):
        resolve_isolation_mode("mystery")


def test_launcher_and_observer_form_one_process_lifecycle(tmp_path: Path) -> None:
    script = tmp_path / "echo.py"
    input_path = tmp_path / "input.txt"
    output_path = tmp_path / "output.txt"
    error_path = tmp_path / "error.txt"
    script.write_text("import sys; print(sys.stdin.read().strip().upper())\n", encoding="utf-8")
    input_path.write_text("hello\n", encoding="utf-8")

    started = time.monotonic()
    process = ProcessLauncher().launch(
        LaunchRequest(
            work_dir=tmp_path,
            run_argv=["python3", str(script)],
            stdin_path=input_path,
            stdout_path=output_path,
            stderr_path=error_path,
            sandbox="none",
        )
    )
    observation = LinuxProcessObserver().observe(process.pid, started_at=started)
    process.returncode = observation.exit_code

    assert observation.exit_code == 0
    assert observation.signal is None
    assert observation.cpu_ms >= 0
    assert observation.mem_kb > 0
    assert output_path.read_text(encoding="utf-8").strip() == "HELLO"


def test_deadline_guard_marks_and_kills_process_group(tmp_path: Path) -> None:
    process = ProcessLauncher().launch(
        LaunchRequest(
            work_dir=tmp_path,
            run_argv=["python3", "-c", "import time; time.sleep(30)"],
            sandbox="none",
        )
    )
    guard = DeadlineGuard(100)
    guard.arm(process.pid)
    started = time.monotonic()
    observation = LinuxProcessObserver().observe(
        process.pid,
        started_at=started,
        wall_expired=lambda: guard.fired,
    )
    guard.cancel()
    process.returncode = observation.exit_code

    assert guard.fired
    assert observation.killed_by_wall
    assert observation.signal == signal.SIGKILL
    assert observation.wall_ms < 3000
