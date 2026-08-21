from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE_DIR = ROOT / "execution_engine"

TOOLCHAINS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("C++", ("g++", "--version")),
    ("Python", ("python3", "--version")),
    ("Java compiler", ("javac", "-version")),
    ("Java runtime", ("java", "-version")),
    ("Rust", ("rustc", "--version")),
    ("Go", ("go", "version")),
    ("Bash", ("bash", "--version")),
    ("Linux namespaces", ("unshare", "--help")),
)


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> int:
    return subprocess.call(command, cwd=cwd or ROOT, env=env)


def check_toolchains(strict: bool) -> int:
    missing: list[str] = []
    for label, command in TOOLCHAINS:
        executable = command[0]
        if shutil.which(executable) is None:
            missing.append(label)
            print(f"missing  {label:<18} ({executable})")
            continue
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        first = (completed.stdout or completed.stderr or "").splitlines()
        detail = first[0] if first else executable
        print(f"ready    {label:<18} {detail}")

    optional = "bwrap"
    print(f"optional bubblewrap         {'ready' if shutil.which(optional) else 'not installed'}")
    print(f"summary  ready={len(TOOLCHAINS) - len(missing)} missing={len(missing)}")
    return 1 if strict and missing else 0


def describe(bundle_dir: str) -> int:
    sys.path.insert(0, str(ROOT))
    from execution_engine.core.bundle import load_challenge_bundle

    bundle = load_challenge_bundle(Path(bundle_dir))
    payload = {
        "root": str(bundle.root),
        "tests": list(bundle.test_ids),
        "limits": {
            "time_limit_ms": bundle.limits.time_limit_ms,
            "memory_limit_mb": bundle.limits.memory_limit_mb,
            "wall_deadline_ms": bundle.limits.wall_deadline_ms,
        },
        "checker": bundle.checker.kind,
    }
    print(json.dumps(payload, indent=2))
    return 0


def test(patterns: list[str]) -> int:
    command = [sys.executable, "-m", "pytest", "-q", "execution_engine/tests"]
    if patterns:
        command.extend(["-k", " or ".join(patterns)])
    return run(command)


def smoke() -> int:
    sys.path.insert(0, str(ROOT))
    from execution_engine.core.engine import evaluate_bundle
    from execution_engine.core.models import Verdict

    fixture = ENGINE_DIR / "fixtures" / "sum_pair"
    result = evaluate_bundle(fixture, fixture / "main.py", runtime="Python", use_cgroup=False)
    if result.status is not Verdict.ACCEPTED:
        print(json.dumps(result.to_dict(), indent=2), file=sys.stderr)
        return 1
    print(f"smoke accepted {result.tests_passed}/{result.tests_total} cases")
    return 0


def build_image(target: str) -> int:
    specs = {
        "test": ("docker/Dockerfile.test", os.getenv("RUNLINE_ENGINE_TEST_IMAGE", "runline-engine-test")),
        "outer": ("docker/Dockerfile.outer", os.getenv("RUNLINE_ENGINE_IMAGE", "runline-engine-runtime")),
    }
    targets = ["test", "outer"] if target == "both" else [target]
    for item in targets:
        dockerfile, tag = specs[item]
        command = ["docker", "build", "-f", dockerfile, "-t", tag, "."]
        print("+", " ".join(command))
        status = run(command, cwd=ENGINE_DIR)
        if status:
            return status
    return 0


def docker_test(patterns: list[str]) -> int:
    image = os.getenv("RUNLINE_ENGINE_TEST_IMAGE", "runline-engine-test")
    if subprocess.call(["docker", "image", "inspect", image], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
        status = build_image("test")
        if status:
            return status
    command = [
        "docker", "run", "--rm", "--privileged", "--user", "root",
        "-e", "PYTHONPATH=/oj", "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-v", f"{ENGINE_DIR}:/oj/execution_engine:rw", "-w", "/oj", image,
        "python3", "-m", "pytest", "-q", "/oj/execution_engine/tests",
    ]
    if patterns:
        command.extend(["-k", " or ".join(patterns)])
    return run(command)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="python -m execution_engine.tools.cli")
    sub = root.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check-toolchains")
    check.add_argument("--strict", action="store_true")

    show = sub.add_parser("describe")
    show.add_argument("bundle_dir")

    tests = sub.add_parser("test")
    tests.add_argument("patterns", nargs="*")

    docker_tests = sub.add_parser("docker-test")
    docker_tests.add_argument("patterns", nargs="*")

    sub.add_parser("smoke")

    build = sub.add_parser("build-image")
    build.add_argument("target", choices=["test", "outer", "both"], nargs="?", default="test")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "check-toolchains":
        return check_toolchains(args.strict)
    if args.command == "describe":
        return describe(args.bundle_dir)
    if args.command == "test":
        return test(args.patterns)
    if args.command == "docker-test":
        return docker_test(args.patterns)
    if args.command == "smoke":
        return smoke()
    if args.command == "build-image":
        return build_image(args.target)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
