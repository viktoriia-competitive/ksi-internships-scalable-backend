#!/usr/bin/env bash
# Optional CLI helper for debugging the INNER environment.
# The production path is Python: execution_engine/outer/spawn_sandboxed.py
# This script is not on the hot path of the judge pipeline.
#
# Usage (once implemented):
#   ./execution_engine/inner/run_in_jail.sh --workdir /tmp/box -- python3 main.py
#
# Notes:
# - This is not Docker; do not call `docker run` from here.
# - OUTER (pipeline) owns cgroup create/add, wall kill, wait4/measure, compare.
# - INNER is responsible only for FS isolation, no network, and exec of the program.
#
# Current status: stub. Implement the isolation logic in spawn_sandboxed.py first.

set -euo pipefail

echo "run_in_jail.sh: stub. Implement isolation in outer/spawn_sandboxed.py first." >&2
exit 1
