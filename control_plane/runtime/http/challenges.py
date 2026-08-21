"""Challenge catalogue routes for the control-plane API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from control_plane.runtime.contracts.attempts import AttemptCollection, PageInfo as AttemptPageInfo
from control_plane.runtime.contracts.challenges import ChallengeCollection, ChallengeView, PageInfo
from control_plane.runtime.http.dependencies import challenge_service, attempt_service
from control_plane.runtime.http.presenters import attempt_view, challenge_card, challenge_view, internal_phase
from control_plane.runtime.use_cases.commands import ChallengeQuery, AttemptQuery
from control_plane.runtime.use_cases.challenges import ChallengeService
from control_plane.runtime.use_cases.attempts import AttemptService

router = APIRouter(prefix="/challenges", tags=["challenge-catalogue"])

@router.get("", response_model=ChallengeCollection)
async def browse_challenges(
    service: Annotated[ChallengeService, Depends(challenge_service)],
    search: str = Query(""),
    level: str = Query("all"),
    label: str = Query("all"),
    mode: str = Query("all"),
    orderBy: str = Query("shortCode"),
    direction: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    size: int = Query(40, ge=1, le=100),
) -> ChallengeCollection:
    result = await service.list(
        ChallengeQuery(
            search=search,
            level=level,
            label=label,
            mode=mode,
            order_by=orderBy,
            direction=direction,
            index=page,
            size=size,
        )
    )
    return ChallengeCollection(
        entries=[challenge_card(item) for item in result.entries],
        pageInfo=PageInfo(
            index=result.index,
            size=result.size,
            totalEntries=result.total_entries,
            totalPages=result.total_pages,
        ),
    )


@router.get("/{challenge_key}", response_model=ChallengeView)
async def read_challenge(
    challenge_key: str,
    service: Annotated[ChallengeService, Depends(challenge_service)],
) -> ChallengeView:
    return challenge_view(await service.require(challenge_key))


@router.get("/{challenge_key}/attempts", response_model=AttemptCollection)
async def challenge_attempts(
    challenge_key: str,
    challenges: Annotated[ChallengeService, Depends(challenge_service)],
    attempts: Annotated[AttemptService, Depends(attempt_service)],
    page: int = Query(1, ge=1),
    size: int = Query(40, ge=1, le=100),
    phase: str | None = Query(None),
) -> AttemptCollection:
    await challenges.require(challenge_key)
    result = await attempts.list(
        AttemptQuery(
            index=page,
            size=size,
            challenge_key=challenge_key,
            phase=internal_phase(phase),
        )
    )
    return AttemptCollection(
        entries=[attempt_view(item, include_report=False) for item in result.entries],
        pageInfo=AttemptPageInfo(
            index=result.index,
            size=result.size,
            totalEntries=result.total_entries,
            totalPages=result.total_pages,
        ),
    )
