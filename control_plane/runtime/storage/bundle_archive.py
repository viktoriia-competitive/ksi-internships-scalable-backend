from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


def bundle_manifest(bundle_dir: Path) -> dict:
    bundle_dir = bundle_dir.resolve()
    files: list[dict[str, str | int]] = []
    for path in sorted(p for p in bundle_dir.rglob("*") if p.is_file()):
        relative = path.relative_to(bundle_dir).as_posix()
        data = path.read_bytes()
        files.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
        )
    canonical = json.dumps(files, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return {"sha256": hashlib.sha256(canonical).hexdigest(), "files": files}


def snapshot_bundle(bundle_dir: Path, artifacts_root: Path) -> tuple[str, Path, dict]:
    manifest = bundle_manifest(bundle_dir)
    digest = str(manifest["sha256"])
    destination = artifacts_root / digest
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name(destination.name + ".tmp")
        if temp.exists():
            shutil.rmtree(temp)
        shutil.copytree(bundle_dir, temp)
        temp.rename(destination)
    return digest, destination, manifest
