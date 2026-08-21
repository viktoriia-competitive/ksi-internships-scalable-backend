from __future__ import annotations

from control_plane.runtime.core.evaluation_command import EvaluationCommand, WorkClass
from control_plane.runtime.storage.sources import materialized_artifact, artifact_metadata
from control_plane.runtime.worker.evaluation_report import build_evaluation_report
from execution_engine.core.models import SuiteResult, TestResult as JudgeTestResult, Verdict


def test_execution_job_wire_format_round_trips() -> None:
    job = EvaluationCommand("submit:abc", "abc", "p1", "Python", WorkClass.INTERACTIVE, retry_index=3)
    assert EvaluationCommand.decode(job.encode()) == job


def test_artifact_metadata_is_derived_from_language_when_filename_missing() -> None:
    metadata = artifact_metadata(runtime="Python", source_text="print(1)\n", artifact_name=None, media_type=None)
    assert metadata.name == "main.py"
    assert metadata.bytes == 9


def test_materialized_artifact_is_removed_after_worker_scope() -> None:
    with materialized_artifact("print(1)\n", "main.py") as path:
        parent = path.parent
        assert path.read_text(encoding="utf-8") == "print(1)\n"
    assert not parent.exists()


def test_judge_failure_projection_exposes_only_first_failure_details() -> None:
    suite = SuiteResult(
        status=Verdict.WRONG_ANSWER,
        tests_passed=0,
        tests_total=1,
        first_failure_message="token mismatch",
        per_test=[
            JudgeTestResult(
                Verdict.WRONG_ANSWER,
                "case-a",
                0,
                4,
                5,
                800,
                message="token mismatch",
                expected_preview="42\n",
                actual_preview="41\n",
            )
        ],
    )
    payload = build_evaluation_report(suite)
    assert payload["failure"] == {
        "testId": "case-a",
        "message": "token mismatch",
        "inputPreview": "",
        "expectedPreview": "42\n",
        "actualPreview": "41\n",
        "stderrPreview": "",
    }
