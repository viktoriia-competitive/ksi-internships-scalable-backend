from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from control_plane.runtime.http import accounts, attempts, challenges, health
from control_plane.runtime.use_cases.errors import NotFoundError, ValidationError
from control_plane.runtime.storage.session import Database
from control_plane.runtime.persistence.accounts import AccountRepository
from control_plane.runtime.settings import Settings, get_settings

log = logging.getLogger("runline.api")


@dataclass(slots=True)
class RuntimeServices:
    """Process-scoped resources owned by the API lifespan."""

    settings: Settings
    database: Database
    redis: Redis

    def publish_to_app(self, app: FastAPI) -> None:
        # Keep the established state attributes for route compatibility.
        app.state.settings = self.settings
        app.state.db = self.database
        app.state.redis = self.redis
        app.state.runtime = self

    async def prepare(self) -> None:
        if self.settings.auto_create_schema:
            await self.database.create_schema()
        async with self.database.sessions() as session:
            await AccountRepository(session).get_or_create(self.settings.dev_handle)
            await session.commit()

    async def close(self) -> None:
        await self.redis.aclose()
        await self.database.close()


def build_runtime(settings: Settings) -> RuntimeServices:
    return RuntimeServices(
        settings=settings,
        database=Database(settings.database_url),
        redis=Redis.from_url(settings.redis_url, decode_responses=False),
    )


@asynccontextmanager
async def application_lifespan(app: FastAPI) -> AsyncIterator[None]:
    runtime = build_runtime(get_settings())
    runtime.publish_to_app(app)
    await runtime.prepare()
    log.info("Runline API started; storage=postgres transport=redis-streams")
    try:
        yield
    finally:
        await runtime.close()


def install_http_policy(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "resource_not_found", "message": str(exc)}},
    )


async def _bad_request(_: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "invalid_request", "message": str(exc)}},
    )


def install_error_mapping(app: FastAPI) -> None:
    app.add_exception_handler(NotFoundError, _not_found)
    app.add_exception_handler(ValidationError, _bad_request)


def install_routes(app: FastAPI, settings: Settings) -> None:
    app.include_router(health.router)
    api_prefix = settings.api_prefix.rstrip("/") or "/control/v2"
    for router in (challenges.router, attempts.router, accounts.router):
        app.include_router(router, prefix=api_prefix)
