from __future__ import annotations

from execution_engine.core.models import SuiteResult, Verdict


def build_evaluation_report(result: SuiteResult) -> dict:
    per_test = []
    failure = None
    for item in result.per_test:
        row = {
            "testId": item.test_id,
            "status": item.status.value,
            "cpuMs": item.cpu_ms,
            "memKb": item.mem_kb,
            "message": item.message[:500],
        }
        per_test.append(row)
        if failure is None and item.status is not Verdict.ACCEPTED:
            failure = {
                "testId": item.test_id or None,
                "message": item.message[:2000],
                "inputPreview": item.input_preview[:4000],
                "expectedPreview": item.expected_preview[:4000],
                "actualPreview": item.actual_preview[:4000],
                "stderrPreview": item.stderr_preview[:4000],
            }
    if failure is None and result.first_failure_message:
        failure = {
            "testId": None,
            "message": result.first_failure_message[:2000],
            "inputPreview": "",
            "expectedPreview": "",
            "actualPreview": "",
            "stderrPreview": "",
        }
    return {
        "testsPassed": result.tests_passed,
        "testsTotal": result.tests_total,
        "maxCpuMs": result.max_cpu_ms,
        "maxMemKb": result.max_mem_kb,
        "compileMessage": result.compile_message[:4000],
        "firstFailureMessage": result.first_failure_message[:4000],
        "failure": failure,
        "perTest": per_test,
    }
