from __future__ import annotations

import argparse
from pathlib import Path

from execution_engine.worker.service import evaluate_bundle, result_to_json, write_result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate one challenge bundle locally")
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--runtime", default=None)
    parser.add_argument("--run-key", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--all-tests", action="store_true")
    parser.add_argument("--no-cgroup", action="store_true")
    args = parser.parse_args(argv)

    result = evaluate_bundle(
        Path(args.bundle),
        Path(args.source),
        runtime=args.runtime,
        run_key=args.run_key,
        stop_on_first_failure=not args.all_tests,
        use_cgroup=not args.no_cgroup,
    )
    if args.out:
        write_result(Path(args.out), result)
    print(result_to_json(result))
    return 0 if result.status.value == "ACCEPTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
