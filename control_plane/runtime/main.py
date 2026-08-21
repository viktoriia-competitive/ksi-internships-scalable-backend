from __future__ import annotations

from fastapi import FastAPI

from control_plane.runtime.bootstrap import (
    application_lifespan,
    install_error_mapping,
    install_http_policy,
    install_routes,
)
from control_plane.runtime.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Runline Control Plane",
        version="2.0.0",
        lifespan=application_lifespan,
    )
    install_http_policy(app, settings)
    install_error_mapping(app)
    install_routes(app, settings)
    return app


app = create_app()
