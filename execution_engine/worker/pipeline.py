from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from execution_engine.core.engine import EvaluationCoordinator
from execution_engine.core.evaluator import classify_process
from execution_engine.core.models import ExecutionLimits as RunLimits
from execution_engine.core.models import SuiteResult, Verdict
from execution_engine.core.bundle import EvaluatorSpec, ChallengeBundle
from execution_engine.core.sandbox import ProcessSandbox, SandboxResult


@dataclass(frozen=True, slots=True)
class SuiteRequest:
    run_key: str
    runtime: str
    source_path: Path
    tests_dir: Path
    work_dir: Path
    limits: RunLimits
    checker: str = "token"
    checker_path: Path | None = None
    stop_on_first_failure: bool = True
    use_cgroup: bool = True


def list_test_stems(tests_dir: Path):
    inputs = {path.stem for path in Path(tests_dir).glob("*.in")}
    outputs = {path.stem for path in Path(tests_dir).glob("*.out")}
    return sorted(inputs & outputs)


def classify_run(*, exit_code: int | None, cpu_ms: int, mem_kb: int, limits: RunLimits, killed_by_wall: bool, killed_by_oom: bool, signal: int | None = None) -> Verdict:
    return classify_process(
        SandboxResult(
            exit_code=exit_code,
            signal=signal,
            cpu_ms=cpu_ms,
            wall_ms=0,
            mem_kb=mem_kb,
            killed_by_wall=killed_by_wall,
            killed_by_oom=killed_by_oom,
        ),
        limits,
    )


def run_suite(req: SuiteRequest) -> SuiteResult:
    bundle = ChallengeBundle(
        root=Path(req.tests_dir).parent,
        metadata={},
        limits=req.limits,
        tests_dir=Path(req.tests_dir),
        test_ids=tuple(list_test_stems(req.tests_dir)),
        checker=EvaluatorSpec(kind=req.checker, path=req.checker_path),
    )
    return EvaluationCoordinator(sandbox=ProcessSandbox(use_cgroup=req.use_cgroup)).evaluate(
        bundle,
        Path(req.source_path),
        runtime=req.runtime,
        run_key=req.run_key,
        work_dir=Path(req.work_dir),
        stop_on_first_failure=req.stop_on_first_failure,
    )
