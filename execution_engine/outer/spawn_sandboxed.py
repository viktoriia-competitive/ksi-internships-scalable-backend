"""Compatibility facade for contestant process launching."""

from __future__ import annotations

from execution_engine.platform.linux.launcher import LaunchRequest, ProcessLauncher, resolve_isolation_mode

SpawnSpec = LaunchRequest
_LAUNCHER = ProcessLauncher()


def resolve_sandbox_mode(override: str | None = None) -> str:
    return resolve_isolation_mode(override).value


def bwrap_available() -> bool:
    return _LAUNCHER.bubblewrap_available()


def spawn_sandboxed(spec: SpawnSpec):
    return _LAUNCHER.launch(spec)
