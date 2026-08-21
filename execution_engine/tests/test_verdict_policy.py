from __future__ import annotations

import pytest

from execution_engine.core.evaluator import classify_process
from execution_engine.core.models import ExecutionLimits, Verdict
from execution_engine.core.sandbox import SandboxResult


LIMITS = ExecutionLimits(time_limit_ms=100, memory_limit_mb=16)


def sample(**overrides) -> SandboxResult:
    values = dict(
        exit_code=0,
        signal=None,
        cpu_ms=10,
        wall_ms=12,
        mem_kb=1024,
        killed_by_wall=False,
        killed_by_oom=False,
        memory_limit_enforced=True,
        cpu_limit_enforced=True,
    )
    values.update(overrides)
    return SandboxResult(**values)


@pytest.mark.parametrize(
    ("observation", "expected"),
    [
        (sample(), Verdict.OK),
        (sample(killed_by_wall=True), Verdict.TIME_LIMIT),
        (sample(cpu_ms=101), Verdict.TIME_LIMIT),
        (sample(killed_by_oom=True), Verdict.MEMORY_LIMIT),
        (sample(mem_kb=16 * 1024 + 1), Verdict.MEMORY_LIMIT),
        (sample(exit_code=2), Verdict.RUNTIME_ERROR),
        (sample(exit_code=-9, signal=9), Verdict.RUNTIME_ERROR),
    ],
)
def test_verdict_precedence(observation: SandboxResult, expected: Verdict) -> None:
    assert classify_process(observation, LIMITS) is expected


def test_development_mode_does_not_claim_unenforced_cpu_limit() -> None:
    observation = sample(cpu_ms=999, cpu_limit_enforced=False)
    assert classify_process(observation, LIMITS) is Verdict.OK
