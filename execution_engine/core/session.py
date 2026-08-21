from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from execution_engine.core.checking import checker_for
from execution_engine.core.models import SuiteResult, TestResult, Verdict
from execution_engine.core.bundle import ChallengeBundle
from execution_engine.core.runner import PreparedProgram, ProgramRunner
from execution_engine.core.sandbox import SandboxProvider, SandboxRequest
from execution_engine.core.verdicts import VerdictPolicy

_PREVIEW_CHARS = 4000


@dataclass(slots=True)
class SuiteSession:
    bundle: ChallengeBundle
    source_path: Path
    runtime: str
    run_key: str
    work_dir: Path
    sandbox: SandboxProvider
    runner: ProgramRunner
    verdict_policy: VerdictPolicy

    def execute(self, *, stop_after_failure: bool = True) -> SuiteResult:
        tests = self.bundle.test_ids
        if not tests:
            return self._empty_suite()

        program = self.runner.prepare(self.runtime, self.source_path, self.work_dir)
        compile_failure = self._compile_failure(program)
        if compile_failure is not None:
            return compile_failure

        case_results: list[TestResult] = []
        for test_id in tests:
            case = self._execute_case(test_id, program.argv)
            case_results.append(case)
            if stop_after_failure and case.status is not Verdict.ACCEPTED:
                break

        return self._summarize(case_results)

    def _execute_case(self, test_id: str, argv: Sequence[str]) -> TestResult:
        input_path = self.bundle.tests_dir / f"{test_id}.in"
        expected_path = self.bundle.tests_dir / f"{test_id}.out"
        actual_path = self.work_dir / f"case-{test_id}.out"
        error_path = self.work_dir / f"case-{test_id}.err"

        try:
            observation = self.sandbox.execute(
                SandboxRequest(
                    execution_id=f"{self.run_key}.{test_id}",
                    work_dir=self.work_dir,
                    argv=argv,
                    stdin_path=input_path,
                    stdout_path=actual_path,
                    stderr_path=error_path,
                    limits=self.bundle.limits,
                )
            )
            verdict = self.verdict_policy.from_process(observation, self.bundle.limits)
            message = self._execution_message(verdict, observation.exit_code, observation.signal)

            if verdict is Verdict.OK:
                check = checker_for(self.bundle.checker).check(
                    input_path=input_path,
                    expected_path=expected_path,
                    actual_path=actual_path,
                )
                verdict = Verdict.ACCEPTED if check.accepted else Verdict.WRONG_ANSWER
                message = check.message

            failed = verdict is not Verdict.ACCEPTED
            return TestResult(
                status=verdict,
                test_id=test_id,
                exit_code=observation.exit_code,
                cpu_ms=observation.cpu_ms,
                wall_ms=observation.wall_ms,
                mem_kb=observation.mem_kb,
                message=message,
                killed_by_wall=observation.killed_by_wall,
                killed_by_oom=observation.killed_by_oom,
                input_preview=_read_preview(input_path) if failed else "",
                expected_preview=_read_preview(expected_path) if verdict is Verdict.WRONG_ANSWER else "",
                actual_preview=_read_preview(actual_path) if verdict in {Verdict.WRONG_ANSWER, Verdict.RUNTIME_ERROR} else "",
                stderr_preview=_read_preview(error_path) if failed else "",
            )
        except Exception as exc:
            return TestResult(
                status=Verdict.INTERNAL_ERROR,
                test_id=test_id,
                exit_code=None,
                cpu_ms=0,
                wall_ms=0,
                mem_kb=0,
                message=str(exc)[:_PREVIEW_CHARS],
            )

    def _summarize(self, cases: list[TestResult]) -> SuiteResult:
        failures = [case for case in cases if case.status is not Verdict.ACCEPTED]
        terminal = failures[0].status if failures else Verdict.ACCEPTED
        return SuiteResult(
            status=terminal,
            tests_passed=sum(case.status is Verdict.ACCEPTED for case in cases),
            tests_total=len(self.bundle.test_ids),
            max_cpu_ms=max((case.cpu_ms for case in cases), default=0),
            max_mem_kb=max((case.mem_kb for case in cases), default=0),
            first_failure_message=failures[0].message if failures else "",
            per_test=cases,
        )

    def _compile_failure(self, program: PreparedProgram) -> SuiteResult | None:
        result = program.compile_result
        if result.ok:
            return None
        details = result.compiler_stderr or result.compiler_stdout or "compiler rejected source"
        return SuiteResult(
            status=Verdict.COMPILATION_ERROR,
            tests_passed=0,
            tests_total=len(self.bundle.test_ids),
            compile_message=details[:_PREVIEW_CHARS],
            first_failure_message="compilation error",
        )

    def _empty_suite(self) -> SuiteResult:
        return SuiteResult(
            status=Verdict.INTERNAL_ERROR,
            tests_passed=0,
            tests_total=0,
            first_failure_message=f"no runnable test pairs in {self.bundle.tests_dir}",
        )

    @staticmethod
    def _execution_message(verdict: Verdict, exit_code: int | None, signal_number: int | None) -> str:
        if verdict is Verdict.TIME_LIMIT:
            return "time limit exceeded"
        if verdict is Verdict.MEMORY_LIMIT:
            return "memory limit exceeded"
        if verdict is Verdict.RUNTIME_ERROR:
            return f"runtime error exit={exit_code} signal={signal_number}"
        return ""


def _read_preview(path: Path) -> str:
    try:
        raw = path.read_bytes()[: _PREVIEW_CHARS * 2]
    except OSError:
        return ""
    text = raw.decode("utf-8", errors="replace")
    if len(text) <= _PREVIEW_CHARS:
        return text
    return text[:_PREVIEW_CHARS] + "\n…"
