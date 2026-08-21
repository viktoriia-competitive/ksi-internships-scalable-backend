from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHALLENGES = ROOT / "challenge_bank" / "challenges"


def normalized_tokens(text: str) -> list[str]:
    return text.split()


def reference_output(reference: Path, case_input: Path) -> tuple[int, str, str]:
    namespace: dict[str, object] = {"__name__": "runline_audit_reference"}
    try:
        exec(compile(reference.read_text(encoding="utf-8"), str(reference), "exec"), namespace)
        solve = namespace["solve"]
        output = str(solve(case_input.read_text(encoding="utf-8"))).rstrip() + "\n"
        return 0, output, ""
    except Exception as exc:
        return 1, "", repr(exc)


def audit_bundle(bundle: Path) -> list[str]:
    issues: list[str] = []
    manifest_path = bundle / "challenge.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{bundle.name}: invalid challenge.json: {exc}"]

    required = {
        "key",
        "shortCode",
        "name",
        "level",
        "mode",
        "budget",
        "prompt",
        "evaluation",
        "suite",
        "artifact",
    }
    for field in sorted(required - manifest.keys()):
        issues.append(f"{bundle.name}: missing {field}")
    if manifest.get("key") != bundle.name:
        issues.append(f"{bundle.name}: key does not match directory")

    budget = manifest.get("budget") or {}
    for field in ("cpuMillis", "memoryMiB"):
        if not isinstance(budget.get(field), int) or budget[field] <= 0:
            issues.append(f"{bundle.name}: budget.{field} must be a positive integer")

    references = manifest.get("references") or []
    reference_entry = next(
        (entry.get("entry") for entry in references if entry.get("runtime") == "Python"),
        None,
    )
    if not reference_entry:
        return issues + [f"{bundle.name}: Python reference entry is required"]
    reference = bundle / str(reference_entry)

    suite = manifest.get("suite") or {}
    cases_dir = bundle / str(suite.get("directory") or "tests")
    evaluator = ((manifest.get("evaluation") or {}).get("checker") or {"kind": "token"})
    case_inputs = sorted(cases_dir.glob("*.in"))
    declared_cases = int(suite.get("cases") or 0)
    if len(case_inputs) != declared_cases:
        issues.append(f"{bundle.name}: declared {declared_cases} cases, found {len(case_inputs)}")

    for input_path in case_inputs:
        expected_path = input_path.with_suffix(".out")
        if not expected_path.is_file():
            issues.append(f"{bundle.name}: missing {expected_path.name}")
            continue
        returncode, stdout, stderr = reference_output(reference, input_path)
        if returncode != 0:
            issues.append(f"{bundle.name}/{input_path.name}: reference failed: {stderr}")
            continue
        if evaluator.get("kind") == "custom":
            checker_path = bundle / str(evaluator.get("script"))
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as actual:
                actual.write(stdout)
                actual_path = Path(actual.name)
            try:
                checked = subprocess.run(
                    [sys.executable, str(checker_path), str(input_path), str(expected_path), str(actual_path)],
                    text=True,
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
                if checked.returncode != 0 or checked.stdout.split()[:1] != ["1"]:
                    issues.append(f"{bundle.name}/{input_path.name}: custom evaluator rejected reference output")
            finally:
                actual_path.unlink(missing_ok=True)
        elif normalized_tokens(stdout) != normalized_tokens(expected_path.read_text(encoding="utf-8")):
            issues.append(f"{bundle.name}/{input_path.name}: reference output differs from expected")
    return issues


def main() -> int:
    bundles = sorted(
        path for path in CHALLENGES.iterdir()
        if path.is_dir() and (path / "challenge.json").is_file()
    )
    issues = [issue for bundle in bundles for issue in audit_bundle(bundle)]
    if issues:
        print("challenge bank audit failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    index = json.loads((CHALLENGES / "index.json").read_text(encoding="utf-8"))
    bundle_keys = {bundle.name for bundle in bundles}
    index_keys = {item["key"] for item in index}
    if bundle_keys != index_keys:
        print("index/bundle key mismatch")
        return 1
    case_count = sum(len(list((bundle / "tests").glob("*.in"))) for bundle in bundles)
    print(f"audited {len(bundles)} challenge bundles and {case_count} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
