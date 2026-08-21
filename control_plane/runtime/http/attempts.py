"""Attempt ingestion, history, source, and lifecycle routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from control_plane.runtime.contracts.attempts import (
    AttemptCollection,
    AttemptLinks,
    AttemptView,
    LifecycleEventView,
    LifecycleTimeline,
    OpenAttemptRequest,
    OpenAttemptResponse,
    PageInfo,
)
from control_plane.runtime.http.dependencies import get_session, attempt_service
from control_plane.runtime.http.presenters import attempt_view, internal_phase
from control_plane.runtime.persistence.lifecycle import LifecycleRepository
from control_plane.runtime.use_cases.commands import OpenAttemptCommand, AttemptQuery
from control_plane.runtime.use_cases.attempts import AttemptService

router = APIRouter(prefix="/attempts", tags=["attempts"])


@router.post("", response_model=OpenAttemptResponse, status_code=202)
async def open_attempt(
    body: OpenAttemptRequest,
    request: Request,
    service: Annotated[AttemptService, Depends(attempt_service)],
    actor_handle: str | None = Header(default=None, alias="X-Runline-Handle"),
    actor_key: str | None = Header(default=None, alias="X-Runline-Account"),
    request_key: str | None = Header(default=None, alias="Request-Key"),
) -> OpenAttemptResponse:
    created = await service.create(
        OpenAttemptCommand(
            challenge_key=body.challengeKey,
            runtime=body.runtime,
            source_text=body.sourceText,
            artifact_name=body.artifactName,
            media_type=body.mediaType,
        ),
        x_handle=actor_handle,
        x_account_key=actor_key,
        request_key=request_key,
    )
    key = str(created.key)
    return OpenAttemptResponse(
        attempt=attempt_view(created, include_report=False),
        links=AttemptLinks(
            self=str(request.url_for("read_attempt", attempt_key=key)),
            events=str(request.url_for("attempt_timeline", attempt_key=key)),
            source=str(request.url_for("download_attempt_source", attempt_key=key)),
        ),
    )


@router.get("", response_model=AttemptCollection)
async def browse_attempts(
    service: Annotated[AttemptService, Depends(attempt_service)],
    page: int = Query(1, ge=1),
    size: int = Query(40, ge=1, le=100),
    challenge: str | None = Query(None),
    phase: str | None = Query(None),
    actor: str | None = Query(None),
) -> AttemptCollection:
    result = await service.list(
        AttemptQuery(
            index=page,
            size=size,
            challenge_key=challenge,
            phase=internal_phase(phase),
            actor_key=actor,
        )
    )
    return AttemptCollection(
        entries=[attempt_view(item, include_report=False) for item in result.entries],
        pageInfo=PageInfo(
            index=result.index,
            size=result.size,
            totalEntries=result.total_entries,
            totalPages=result.total_pages,
        ),
    )


@router.get("/{attempt_key}", response_model=AttemptView, name="read_attempt")
async def read_attempt(
    attempt_key: str,
    service: Annotated[AttemptService, Depends(attempt_service)],
) -> AttemptView:
    attempt = await service.get(attempt_key)
    return attempt_view(attempt, source_text=attempt.source_text)


@router.get("/{attempt_key}/source", name="download_attempt_source")
async def download_attempt_source(
    attempt_key: str,
    service: Annotated[AttemptService, Depends(attempt_service)],
) -> Response:
    attempt = await service.get(attempt_key)
    safe_name = attempt.artifact_name.replace('"', "").replace("\r", "").replace("\n", "")
    return Response(
        content=attempt.source_text.encode("utf-8"),
        media_type=attempt.media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.get("/{attempt_key}/timeline", response_model=LifecycleTimeline, name="attempt_timeline")
async def attempt_timeline(
    attempt_key: str,
    service: Annotated[AttemptService, Depends(attempt_service)],
    session: AsyncSession = Depends(get_session),
) -> LifecycleTimeline:
    await service.get(attempt_key)
    events = await LifecycleRepository(session).list_for_attempt(attempt_key)
    return LifecycleTimeline(
        entries=[
            LifecycleEventView(
                index=event.sequence,
                event=event.event_type.casefold().replace("_", "."),
                recordedAt=event.occurred_at.isoformat().replace("+00:00", "Z"),
                runKey=event.run_key,
                deliveryKey=event.delivery_key,
                attributes=event.payload,
            )
            for event in events
        ]
    )
