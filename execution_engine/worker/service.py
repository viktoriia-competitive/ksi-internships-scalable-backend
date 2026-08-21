from __future__ import annotations

import json
from pathlib import Path

from execution_engine.core.engine import evaluate_bundle
from execution_engine.core.models import SuiteResult


def result_to_json(result: SuiteResult, *, indent: int = 2) -> str:
    return json.dumps(result.to_dict(), indent=indent, ensure_ascii=False)


def write_result(path: Path, result: SuiteResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result_to_json(result) + "\n", encoding="utf-8")


__all__ = ["evaluate_bundle", "result_to_json", "write_result"]
