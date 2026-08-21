from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Verdict(str, Enum):
    OK = "OK"
    ACCEPTED = "ACCEPTED"
    WRONG_ANSWER = "WRONG_ANSWER"
    TIME_LIMIT = "TIME_LIMIT"
    MEMORY_LIMIT = "MEMORY_LIMIT"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True, slots=True)
class ExecutionLimits:
    time_limit_ms: int
    memory_limit_mb: int
    wall_factor: float = 2.0
    pids_max: int = 128

    @property
    def wall_deadline_ms(self) -> int:
        cpu = max(1, int(self.time_limit_ms))
        return max(cpu, int(cpu * self.wall_factor))

    @classmethod
    def from_mapping(cls, raw: dict[str, Any], wall_factor: float = 2.0) -> "ExecutionLimits":
        return cls(
            time_limit_ms=int(raw["timeLimitMs"]),
            memory_limit_mb=int(raw["memoryLimitMb"]),
            wall_factor=wall_factor,
        )

@dataclass(slots=True)
class TestResult:
    status: Verdict
    test_id: str
    exit_code: int | None
    cpu_ms: int
    wall_ms: int
    mem_kb: int
    message: str = ""
    killed_by_wall: bool = False
    killed_by_oom: bool = False
    input_preview: str = ""
    expected_preview: str = ""
    actual_preview: str = ""
    stderr_preview: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


@dataclass(slots=True)
class SuiteResult:
    status: Verdict
    tests_passed: int
    tests_total: int
    max_cpu_ms: int = 0
    max_mem_kb: int = 0
    compile_message: str = ""
    first_failure_message: str = ""
    per_test: list[TestResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "tests_passed": self.tests_passed,
            "tests_total": self.tests_total,
            "max_cpu_ms": self.max_cpu_ms,
            "max_mem_kb": self.max_mem_kb,
            "compile_message": self.compile_message,
            "first_failure_message": self.first_failure_message,
            "per_test": [item.to_dict() for item in self.per_test],
        }
