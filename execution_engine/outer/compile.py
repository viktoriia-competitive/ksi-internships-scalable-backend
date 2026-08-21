"""Language preparation strategies for trusted-side execution."""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

COMPILE_WALL_S = 30.0
SUPPORTED_LANGUAGES = ("C++", "Python", "Java", "Rust", "Go", "Bash", "SQL")


@dataclass(slots=True)
class CompileResult:
    ok: bool
    language: str
    run_argv: Sequence[str]
    artifact_path: Path | None
    compiler_stderr: str = ""
    compiler_stdout: str = ""
    wall_ms: int = 0


_ALIASES = {
    "c++": "C++",
    "cpp": "C++",
    "cxx": "C++",
    "python": "Python",
    "python3": "Python",
    "py": "Python",
    "java": "Java",
    "rust": "Rust",
    "go": "Go",
    "golang": "Go",
    "bash": "Bash",
    "sh": "Bash",
    "sql": "SQL",
}


def _normalize_language(language: str) -> str:
    stripped = language.strip()
    return _ALIASES.get(stripped.lower(), stripped)


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))


def _failure(language: str, started: float, message: str) -> CompileResult:
    return CompileResult(False, language, [], None, compiler_stderr=message, wall_ms=_elapsed_ms(started))


def _copy_script(
    language: str,
    source: Path,
    work_dir: Path,
    *,
    filename: str,
    argv_builder: Callable[[Path], Sequence[str]],
    executable: bool = False,
) -> CompileResult:
    started = time.monotonic()
    target = work_dir / filename
    if source != target.resolve():
        shutil.copy2(source, target)
    if executable:
        target.chmod(target.stat().st_mode | 0o111)
    return CompileResult(
        True,
        language,
        list(argv_builder(target)),
        target,
        wall_ms=_elapsed_ms(started),
    )


def _prepare_python(source: Path, work_dir: Path) -> CompileResult:
    return _copy_script("Python", source, work_dir, filename="main.py", argv_builder=lambda p: ["python3", str(p)])


def _prepare_bash(source: Path, work_dir: Path) -> CompileResult:
    return _copy_script("Bash", source, work_dir, filename="main.sh", argv_builder=lambda p: ["bash", str(p)], executable=True)


def _prepare_cpp(source: Path, work_dir: Path) -> CompileResult:
    started = time.monotonic()
    output = work_dir / "main"
    command = ["g++", "-O2", "-std=c++17", "-pipe", "-o", str(output), str(source)]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=COMPILE_WALL_S,
            check=False,
        )
    except FileNotFoundError:
        return _failure("C++", started, "g++ not found on PATH")
    except subprocess.TimeoutExpired as exc:
        return CompileResult(
            False,
            "C++",
            [],
            None,
            compiler_stderr=(exc.stderr or "") + "\ncompile timed out",
            compiler_stdout=exc.stdout or "",
            wall_ms=_elapsed_ms(started),
        )

    ok = completed.returncode == 0 and output.is_file()
    return CompileResult(
        ok,
        "C++",
        [str(output)] if ok else [],
        output if ok else None,
        compiler_stderr=completed.stderr or "",
        compiler_stdout=completed.stdout or "",
        wall_ms=_elapsed_ms(started),
    )


_PREPARERS: dict[str, Callable[[Path, Path], CompileResult]] = {
    "Python": _prepare_python,
    "Bash": _prepare_bash,
    "C++": _prepare_cpp,
}


def compile_source(language: str, source_path: Path, work_dir: Path) -> CompileResult:
    normalized = _normalize_language(language)
    source = Path(source_path).resolve()
    destination = Path(work_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()

    if normalized not in SUPPORTED_LANGUAGES:
        return _failure(normalized, started, f"unsupported language: {normalized}")
    if not source.is_file():
        return _failure(normalized, started, f"source not found: {source}")

    preparer = _PREPARERS.get(normalized)
    if preparer is None:
        return _failure(normalized, started, f"language not implemented yet: {normalized}")
    return preparer(source, destination)
