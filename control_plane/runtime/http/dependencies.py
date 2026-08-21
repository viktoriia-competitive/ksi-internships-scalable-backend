from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from control_plane.runtime.use_cases.challenges import ChallengeService
from control_plane.runtime.use_cases.attempts import AttemptService
from control_plane.runtime.use_cases.accounts import AccountService
from control_plane.runtime.storage.transaction import SqlAlchemyTransaction
from control_plane.runtime.persistence.lifecycle import LifecycleRepository
from control_plane.runtime.persistence.outbox import OutboxRepository
from control_plane.runtime.persistence.challenges import ChallengeRepository
from control_plane.runtime.persistence.revisions import ChallengeRevisionRepository
from control_plane.runtime.persistence.attempts import AttemptRepository
from control_plane.runtime.persistence.accounts import AccountRepository


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.db.sessions() as session:
        yield session


def challenge_service(session: AsyncSession = Depends(get_session)) -> ChallengeService:
    return ChallengeService(ChallengeRepository(session))


def attempt_service(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AttemptService:
    settings = request.app.state.settings
    return AttemptService(
        SqlAlchemyTransaction(session),
        attempts=AttemptRepository(session),
        challenges=ChallengeRepository(session),
        accounts=AccountRepository(session),
        outbox=OutboxRepository(session),
        dev_handle=settings.dev_handle,
        events=LifecycleRepository(session),
        revisions=ChallengeRevisionRepository(session),
    )


def account_service(request: Request, session: AsyncSession = Depends(get_session)) -> AccountService:
    return AccountService(
        AccountRepository(session),
        SqlAlchemyTransaction(session),
        default_handle=request.app.state.settings.dev_handle,
    )
