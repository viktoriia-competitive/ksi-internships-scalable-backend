from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ChallengeSeed:
    key: str
    short_code: str
    name: str
    level: str
    score: int | None
    accepted_count: int
    mode: str
    labels: list[str]
    runtimes: list[str]
    budget: dict[str, int | bool]
    profile: dict[str, Any]


def load_challenge_bundle(bundle_dir: Path, repo_root: Path) -> ChallengeSeed:
    bundle_dir = bundle_dir.resolve()
    raw = json.loads((bundle_dir / "challenge.json").read_text(encoding="utf-8"))
    challenge_key = str(raw["key"])
    budget = raw.get("budget") or {}
    if "cpuMillis" not in budget or "memoryMiB" not in budget:
        raise ValueError(f"{challenge_key}: missing execution budget")

    statement_markdown = None
    statement_file = bundle_dir / "statement.md"
    if statement_file.is_file():
        statement_markdown = statement_file.read_text(encoding="utf-8")

    suite = dict(raw.get("suite") or {})
    suite_dir = bundle_dir / str(suite.get("directory") or "tests")
    suite["directory"] = suite.get("directory") or "tests"
    suite["cases"] = int(suite.get("cases") or 0)
    suite["visible"] = int(suite.get("visible") or 0)
    suite["complete"] = bool(suite.get("complete", False))
    suite["ref"] = _repo_relative(suite_dir, repo_root)

    evaluation = dict(raw.get("evaluation") or {})
    evaluator = dict(evaluation.get("checker") or {"kind": "token"})
    if evaluator.get("kind") == "custom" and evaluator.get("script"):
        evaluator["ref"] = _repo_relative(bundle_dir / str(evaluator["script"]), repo_root)
    evaluation["checker"] = evaluator

    details = {
        "origin": raw.get("origin") or {},
        "budgetDerived": bool(budget.get("derived", False)),
        "input": raw.get("input") or {"mode": "stdio"},
        "prompt": {
            **dict(raw.get("prompt") or {}),
            "markdown": statement_markdown,
        },
        "examples": list(raw.get("examples") or []),
        "evaluation": evaluation,
        "suite": suite,
        "artifact": raw.get("artifact") or {"kind": "source"},
        "references": list(raw.get("references") or []),
        "assets": list(raw.get("assets") or []),
        "enabled": bool(raw.get("enabled", True)),
    }
    return ChallengeSeed(
        key=challenge_key,
        short_code=str(raw.get("shortCode") or challenge_key),
        name=str(raw.get("name") or challenge_key),
        level=str(raw.get("level") or "easy"),
        score=raw.get("score"),
        accepted_count=int(raw.get("acceptedCount") or 0),
        mode=str(raw.get("mode") or "stdio"),
        labels=[str(tag) for tag in raw.get("labels") or []],
        runtimes=[str(runtime) for runtime in raw.get("runtimes") or []],
        budget={
            "cpuMillis": int(budget["cpuMillis"]),
            "memoryMiB": int(budget["memoryMiB"]),
            "derived": bool(budget.get("derived", False)),
        },
        profile=details,
    )


def discover_bundles(challenges_root: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in challenges_root.iterdir()
            if path.is_dir() and (path / "challenge.json").is_file()
        ),
        key=lambda path: path.name,
    )


def _repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return f"file:{path.resolve().as_posix()}"
