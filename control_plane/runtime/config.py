"""Compatibility import for scripts that previously used control_plane.runtime.config."""
from control_plane.runtime.settings import REPO_ROOT, Settings, get_settings

__all__ = ["REPO_ROOT", "Settings", "get_settings"]
