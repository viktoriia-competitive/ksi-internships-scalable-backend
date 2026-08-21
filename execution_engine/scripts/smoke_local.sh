#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
cd "$ROOT"
python3 execution_engine/scripts/sync_schemas.py >/dev/null
python3 -m execution_engine.tools.cli smoke
python3 -m execution_engine.tools.cli test
