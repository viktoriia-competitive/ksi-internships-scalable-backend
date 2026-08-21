from __future__ import annotations

from dataclasses import dataclass

from execution_engine.core.models import ExecutionLimits, Verdict
from execution_engine.core.sandbox import SandboxResult


@dataclass(frozen=True, slots=True)
class VerdictPolicy:
    """Translate host observations into a contestant-facing execution verdict."""

    def from_process(self, observation: SandboxResult, limits: ExecutionLimits) -> Verdict:
        if observation.killed_by_oom:
            return Verdict.MEMORY_LIMIT
        if observation.killed_by_wall:
            return Verdict.TIME_LIMIT
        if observation.cpu_limit_enforced and observation.cpu_ms > limits.time_limit_ms:
            return Verdict.TIME_LIMIT
        memory_ceiling_kb = limits.memory_limit_mb * 1024
        if observation.memory_limit_enforced and observation.mem_kb > memory_ceiling_kb:
            return Verdict.MEMORY_LIMIT
        if observation.signal or observation.exit_code not in {0}:
            return Verdict.RUNTIME_ERROR
        return Verdict.OK
