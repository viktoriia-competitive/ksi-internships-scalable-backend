"""Compatibility functions backed by the v2 verdict and output-checking policies."""
from __future__ import annotations

from pathlib import Path

from execution_engine.core.checking import checker_for
from execution_engine.core.models import ExecutionLimits, Verdict
from execution_engine.core.bundle import EvaluatorSpec
from execution_engine.core.sandbox import SandboxResult
from execution_engine.core.verdicts import VerdictPolicy

_POLICY = VerdictPolicy()


def classify_process(sample: SandboxResult, limits: ExecutionLimits) -> Verdict:
    return _POLICY.from_process(sample, limits)


def compare_output(checker: EvaluatorSpec, stdin_path: Path, expected_path: Path, actual_path: Path) -> tuple[bool, str]:
    outcome = checker_for(checker).check(
        input_path=stdin_path,
        expected_path=expected_path,
        actual_path=actual_path,
    )
    return outcome.accepted, outcome.message
