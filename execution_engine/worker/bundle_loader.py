from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from execution_engine.core.models import ExecutionLimits as RunLimits
from execution_engine.core.bundle import load_challenge_bundle


@dataclass(frozen=True, slots=True)
class LoadedBundle:
    root: Path
    challenge: dict[str, Any]
    limits: RunLimits
    tests_dir: Path
    test_stems: list[str]
    model_paths: list[Path]


def load_bundle(bundle_dir: Path, *, wall_factor: float = 2.0) -> LoadedBundle:
    bundle = load_challenge_bundle(Path(bundle_dir), wall_factor=wall_factor)
    models = [
        bundle.root / str(item["entry"])
        for item in bundle.metadata.get("references") or []
        if isinstance(item, dict) and item.get("entry") and (bundle.root / str(item["entry"])).is_file()
    ]
    return LoadedBundle(
        root=bundle.root,
        challenge=bundle.metadata,
        limits=bundle.limits,
        tests_dir=bundle.tests_dir,
        test_stems=list(bundle.test_ids),
        model_paths=models,
    )


def limits_summary(bundle: LoadedBundle) -> dict[str, Any]:
    return {
        "challenge_key": bundle.challenge.get("key"),
        "scope": "per_test",
        "cpu_millis": bundle.limits.time_limit_ms,
        "memory_mib": bundle.limits.memory_limit_mb,
        "wall_deadline_ms": bundle.limits.wall_deadline_ms,
        "case_count": len(bundle.test_stems),
    }
