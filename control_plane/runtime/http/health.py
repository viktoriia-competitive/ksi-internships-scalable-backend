from __future__ import annotations

from fastapi import APIRouter, Request, Response
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"state": "alive"}


@router.get("/ready")
async def ready(request: Request, response: Response) -> dict[str, str]:
    try:
        async with request.app.state.db.sessions() as session:
            await session.execute(text("SELECT 1"))
        await request.app.state.redis.ping()
    except Exception:
        response.status_code = 503
        return {"state": "blocked"}
    return {"state": "ready"}
