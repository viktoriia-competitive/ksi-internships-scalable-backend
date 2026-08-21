from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from execution_engine.core.models import ExecutionLimits


@dataclass(frozen=True, slots=True)
class EvaluatorSpec:
    kind: str = "token"
    path: Path | None = None


@dataclass(frozen=True, slots=True)
class ChallengeBundle:
    root: Path
    metadata: dict[str, Any]
    limits: ExecutionLimits
    tests_dir: Path
    test_ids: tuple[str, ...]
    checker: EvaluatorSpec


def load_challenge_bundle(root: Path, *, wall_factor: float = 2.0) -> ChallengeBundle:
    root = root.resolve()
    metadata_path = root / "challenge.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"missing challenge.json in {root}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    budget = metadata.get("budget") or {}
    if "cpuMillis" not in budget or "memoryMiB" not in budget:
        raise ValueError(f"{metadata_path}: execution budget is required")
    limits_raw = {
        "timeLimitMs": budget["cpuMillis"],
        "memoryLimitMb": budget["memoryMiB"],
    }

    suite = metadata.get("suite") or {}
    tests_dir = root / str(suite.get("directory") or "tests")
    test_ids = _discover_tests(tests_dir)

    evaluation = metadata.get("evaluation") or {}
    checker_raw = evaluation.get("checker") or {}
    if isinstance(checker_raw, str):
        checker = EvaluatorSpec(kind=checker_raw.lower())
    else:
        kind = str(checker_raw.get("kind") or "token").lower()
        path = None
        if kind == "custom":
            path = root / str(checker_raw.get("script") or "checker.py")
        checker = EvaluatorSpec(kind=kind, path=path)

    return ChallengeBundle(
        root=root,
        metadata=metadata,
        limits=ExecutionLimits.from_mapping(limits_raw, wall_factor),
        tests_dir=tests_dir,
        test_ids=test_ids,
        checker=checker,
    )


def _discover_tests(tests_dir: Path) -> tuple[str, ...]:
    if not tests_dir.is_dir():
        return ()
    inputs = {path.stem for path in tests_dir.glob("*.in")}
    outputs = {path.stem for path in tests_dir.glob("*.out")}
    return tuple(sorted(inputs & outputs))
