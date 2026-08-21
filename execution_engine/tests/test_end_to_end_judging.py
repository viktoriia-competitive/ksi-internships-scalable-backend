from __future__ import annotations

from pathlib import Path

from execution_engine.core.engine import evaluate_bundle
from execution_engine.core.models import Verdict


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_known_good_solution_is_accepted() -> None:
    result = evaluate_bundle(
        FIXTURES / "sum_pair",
        FIXTURES / "sum_pair" / "main.py",
        runtime="Python",
        use_cgroup=False,
    )
    assert result.status is Verdict.ACCEPTED
    assert result.tests_passed == result.tests_total == 2


def test_wrong_solution_reports_first_failed_case() -> None:
    result = evaluate_bundle(
        FIXTURES / "intentional_wa",
        FIXTURES / "intentional_wa" / "main.py",
        runtime="Python",
        use_cgroup=False,
    )
    assert result.status is Verdict.WRONG_ANSWER
    assert result.tests_passed < result.tests_total
    assert result.first_failure_message
    assert any(case.status is Verdict.WRONG_ANSWER for case in result.per_test)
