#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from execution_engine.contracts.schema_catalog import SCHEMAS  # noqa: E402


def main() -> int:
    target = ROOT / "execution_engine" / "schemas"
    target.mkdir(parents=True, exist_ok=True)
    for filename, factory in SCHEMAS.items():
        path = target / filename
        path.write_text(json.dumps(factory(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
