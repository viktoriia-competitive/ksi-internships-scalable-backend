from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://runline:runline@127.0.0.1:5432/runline"
    redis_url: str = "redis://127.0.0.1:6379/0"
    api_prefix: str = "/control/v2"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    dev_handle: str = "dev"
    queue_namespace: str = "runline-control"
    queue_group: str = "evaluation-workers"
    queue_max_attempts: int = 3
    queue_visibility_timeout_ms: int = 60_000
    result_channel: str = "runline-control:evaluation-results"

    auto_create_schema: bool = True

    execution_use_cgroup: bool = False
    execution_isolation: str = "none"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
