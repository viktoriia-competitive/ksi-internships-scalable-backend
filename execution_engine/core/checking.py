from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from execution_engine.core.bundle import EvaluatorSpec


@dataclass(frozen=True, slots=True)
class CheckOutcome:
    accepted: bool
    message: str = ""


class OutputChecker(Protocol):
    def check(self, *, input_path: Path, expected_path: Path, actual_path: Path) -> CheckOutcome: ...


@dataclass(frozen=True, slots=True)
class WhitespaceTokenChecker:
    encoding: str = "utf-8"

    def check(self, *, input_path: Path, expected_path: Path, actual_path: Path) -> CheckOutcome:
        del input_path
        expected_tokens = expected_path.read_text(encoding=self.encoding, errors="replace").split()
        actual_tokens = actual_path.read_text(encoding=self.encoding, errors="replace").split()
        if expected_tokens == actual_tokens:
            return CheckOutcome(True)

        mismatch = _first_difference(expected_tokens, actual_tokens)
        return CheckOutcome(False, mismatch)


@dataclass(frozen=True, slots=True)
class PythonScoreChecker:
    script: Path
    timeout_seconds: float = 10.0

    def check(self, *, input_path: Path, expected_path: Path, actual_path: Path) -> CheckOutcome:
        if not self.script.is_file():
            return CheckOutcome(False, f"checker not found: {self.script}")

        try:
            completed = subprocess.run(
                ["python3", str(self.script), str(input_path), str(expected_path), str(actual_path)],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return CheckOutcome(False, "checker timed out")

        if completed.returncode != 0:
            details = (completed.stderr or completed.stdout or "").strip()
            return CheckOutcome(False, f"checker failed ({completed.returncode}): {details}".rstrip())

        first_line = next(iter((completed.stdout or "").splitlines()), "").strip()
        try:
            score = float(first_line.split()[0])
        except (ValueError, IndexError):
            return CheckOutcome(False, "checker did not return a numeric score")

        accepted = score >= 1.0 - 1e-9
        return CheckOutcome(accepted, "" if accepted else f"checker score={score:g}")


def checker_for(spec: EvaluatorSpec) -> OutputChecker:
    kind = spec.kind.casefold()
    if kind in {"token", "tokens", "whitespace"}:
        return WhitespaceTokenChecker()
    if kind == "custom":
        if spec.path is None:
            return _RejectingChecker("custom checker path missing")
        return PythonScoreChecker(spec.path)
    return _RejectingChecker(f"unknown checker: {spec.kind}")


@dataclass(frozen=True, slots=True)
class _RejectingChecker:
    reason: str

    def check(self, *, input_path: Path, expected_path: Path, actual_path: Path) -> CheckOutcome:
        del input_path, expected_path, actual_path
        return CheckOutcome(False, self.reason)


def _first_difference(expected: list[str], actual: list[str]) -> str:
    common = min(len(expected), len(actual))
    for index in range(common):
        if expected[index] != actual[index]:
            return f"token {index + 1} differs"
    if len(expected) != len(actual):
        return f"token count differs: expected {len(expected)}, got {len(actual)}"
    return "token mismatch"
