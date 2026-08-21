from __future__ import annotations

import json
from pathlib import Path

import pytest

from execution_engine.core.bundle import load_challenge_bundle


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_bundle_loader_discovers_only_complete_input_output_pairs() -> None:
    bundle = load_challenge_bundle(FIXTURES / "sum_pair")
    assert bundle.test_ids == ("01", "02")
    assert bundle.limits.time_limit_ms > 0
    assert bundle.limits.memory_limit_mb > 0


def test_bundle_without_manifest_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_challenge_bundle(tmp_path)


def test_bundle_requires_execution_budget(tmp_path: Path) -> None:
    (tmp_path / "challenge.json").write_text(json.dumps({"key": "broken"}), encoding="utf-8")
    with pytest.raises(ValueError, match="execution budget"):
        load_challenge_bundle(tmp_path)


def test_unpaired_test_files_are_not_scheduled(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "01.in").write_text("1\n", encoding="utf-8")
    (tmp_path / "tests" / "02.out").write_text("2\n", encoding="utf-8")
    (tmp_path / "challenge.json").write_text(
        json.dumps({"budget": {"cpuMillis": 100, "memoryMiB": 16}, "suite": {"directory": "tests"}}),
        encoding="utf-8",
    )
    assert load_challenge_bundle(tmp_path).test_ids == ()
