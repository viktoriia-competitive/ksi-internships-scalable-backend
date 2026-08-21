from __future__ import annotations

import hashlib
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True, slots=True)
class ArtifactMetadata:
    name: str
    media_type: str
    bytes: int
    digest: str


_EXTENSIONS = {
    "python": ".py",
    "c++": ".cpp",
    "cpp": ".cpp",
    "java": ".java",
    "rust": ".rs",
    "go": ".go",
    "bash": ".sh",
    "sql": ".sql",
}
_CONTENT_TYPES = {
    ".py": "text/x-python",
    ".cpp": "text/x-c++src",
    ".cc": "text/x-c++src",
    ".java": "text/x-java-source",
    ".rs": "text/x-rustsrc",
    ".go": "text/x-go",
    ".sh": "text/x-shellscript",
    ".sql": "application/sql",
}


def artifact_metadata(
    *,
    runtime: str,
    source_text: str,
    artifact_name: str | None,
    media_type: str | None,
) -> ArtifactMetadata:
    extension = _extension(runtime, artifact_name)
    name = Path(artifact_name or f"main{extension}").name
    encoded = source_text.encode("utf-8")
    return ArtifactMetadata(
        name=name,
        media_type=media_type or _CONTENT_TYPES.get(extension, "text/plain"),
        bytes=len(encoded),
        digest=hashlib.sha256(encoded).hexdigest(),
    )


@contextmanager
def materialized_artifact(source_text: str, artifact_name: str) -> Iterator[Path]:
    """Create an ephemeral worker-local source artifact."""
    with tempfile.TemporaryDirectory(prefix="runline-artifact-") as directory:
        path = Path(directory) / Path(artifact_name).name
        path.write_text(source_text, encoding="utf-8")
        yield path


def _extension(runtime: str, artifact_name: str | None) -> str:
    if artifact_name:
        suffixes = Path(artifact_name).suffixes
        if suffixes:
            return "".join(suffixes[-2:]) if suffixes[-2:] == [".tar", ".gz"] else suffixes[-1]
    return _EXTENSIONS.get(runtime.strip().lower(), ".txt")
