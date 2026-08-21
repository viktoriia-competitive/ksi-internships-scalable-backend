"""Legacy output-checking API kept for callers outside the v2 core."""
from __future__ import annotations

from pathlib import Path

from execution_engine.core.checking import PythonScoreChecker, WhitespaceTokenChecker

CHECKER_TIMEOUT_S = 10.0
_TOKENS = WhitespaceTokenChecker()


def token_compare(expected: str, actual: str) -> bool:
    return expected.split() == actual.split()


def token_compare_files(expected_path: Path, actual_path: Path) -> bool:
    # The compatibility function intentionally exposes the historical signature.
    return _TOKENS.check(
        input_path=Path("."),
        expected_path=Path(expected_path),
        actual_path=Path(actual_path),
    ).accepted


def run_custom_checker(
    checker_path: Path,
    input_path: Path,
    expected_path: Path,
    actual_path: Path,
    *,
    timeout_s: float = CHECKER_TIMEOUT_S,
) -> float:
    outcome = PythonScoreChecker(Path(checker_path), timeout_seconds=timeout_s).check(
        input_path=Path(input_path),
        expected_path=Path(expected_path),
        actual_path=Path(actual_path),
    )
    return 1.0 if outcome.accepted else 0.0
