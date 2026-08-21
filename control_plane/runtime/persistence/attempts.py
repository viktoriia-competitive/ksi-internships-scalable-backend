from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from control_plane.runtime.storage.models import AttemptProjectionRow, AttemptRow
from control_plane.runtime.core.entities import Attempt, NewAttempt, PageSlice
from control_plane.runtime.core.status import TERMINAL_STATUSES


def _snapshot(row: AttemptRow, projection: AttemptProjectionRow | None = None) -> Attempt:
    return Attempt(
        key=row.key,
        account_key=row.account_key,
        actor_handle=row.actor_handle,
        challenge_key=row.challenge_key,
        challenge_short_code=row.challenge_short_code,
        challenge_name=row.challenge_name,
        runtime=row.runtime,
        phase=projection.phase if projection is not None else row.phase,
        artifact_ref=row.artifact_ref,
        source_text=row.source_text,
        artifact_name=row.artifact_name,
        media_type=row.media_type,
        artifact_bytes=int(row.artifact_bytes or 0),
        report=dict(projection.report or {}) if projection is not None else dict(row.report or {}),
        work_key=row.work_key,
        request_key=row.request_key,
        created_at=row.created_at,
        started_at=projection.started_at if projection is not None else row.started_at,
        finished_at=projection.finished_at if projection is not None else row.finished_at,
    )


class AttemptRepository:
    """SQLAlchemy implementation of attempt persistence and state transitions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, item: NewAttempt) -> Attempt:
        row = AttemptRow(
            key=item.key,
            account_key=item.account_key,
            actor_handle=item.actor_handle,
            challenge_key=item.challenge_key,
            challenge_short_code=item.challenge_short_code,
            challenge_name=item.challenge_name,
            runtime=item.runtime,
            phase=item.phase,
            artifact_ref=item.artifact_ref,
            source_text=item.source_text,
            artifact_name=item.artifact_name,
            media_type=item.media_type,
            artifact_bytes=item.artifact_bytes,
            report=dict(item.report),
            work_key=item.work_key,
            request_key=item.request_key,
            created_at=item.created_at,
        )
        self._session.add(row)
        await self._session.flush()
        return _snapshot(row)

    async def get(self, attempt_key: str) -> Attempt | None:
        sid = self._uuid_or_none(attempt_key)
        if sid is None:
            return None
        row = await self._session.get(AttemptRow, sid)
        if row is None:
            return None
        projection = await self._session.get(AttemptProjectionRow, sid)
        return _snapshot(row, projection)

    async def get_by_request_key(self, account_key: uuid.UUID, key: str) -> Attempt | None:
        row = await self._session.scalar(
            select(AttemptRow).where(
                AttemptRow.account_key == account_key,
                AttemptRow.request_key == key,
            )
        )
        return _snapshot(row) if row is not None else None

    async def page(
        self,
        *,
        index: int,
        size: int,
        challenge_key: str | None,
        phase: str | None,
        actor_key: str | None,
    ) -> PageSlice[Attempt]:
        size = min(max(int(size), 1), 100)
        requested_page = max(int(index), 1)
        predicates = []
        if challenge_key:
            predicates.append(AttemptRow.challenge_key == challenge_key)
        if phase:
            predicates.append(AttemptRow.phase == phase)
        if actor_key:
            account_uuid = self._uuid_or_none(actor_key)
            if account_uuid is None:
                raise ValueError("invalid account key")
            predicates.append(AttemptRow.account_key == account_uuid)

        count_query = select(func.count()).select_from(AttemptRow)
        if predicates:
            count_query = count_query.where(*predicates)
        total = int(await self._session.scalar(count_query) or 0)
        pages = max(1, math.ceil(total / size))
        current = min(requested_page, pages)

        query = select(AttemptRow)
        if predicates:
            query = query.where(*predicates)
        query = (
            query.order_by(AttemptRow.created_at.desc())
            .offset((current - 1) * size)
            .limit(size)
        )
        rows = list((await self._session.scalars(query)).all())
        projections = {}
        if rows:
            ids = [row.key for row in rows]
            projection_rows = list(
                (
                    await self._session.scalars(
                        select(AttemptProjectionRow).where(AttemptProjectionRow.attempt_key.in_(ids))
                    )
                ).all()
            )
            projections = {item.attempt_key: item for item in projection_rows}
        return PageSlice(
            entries=[_snapshot(row, projections.get(row.key)) for row in rows],
            total_entries=total,
            index=current,
            size=size,
            total_pages=pages,
        )

    async def claim_for_execution(
        self,
        attempt_key: str,
        work_key: str,
        *,
        allow_running: bool = False,
    ) -> Attempt | None:
        sid = self._uuid_or_none(attempt_key)
        if sid is None:
            return None
        now = datetime.now(timezone.utc)
        eligible = ["QUEUED", "RUNNING"] if allow_running else ["QUEUED"]
        statement = (
            update(AttemptRow)
            .where(
                AttemptRow.key == sid,
                AttemptRow.work_key == work_key,
                AttemptRow.phase.in_(eligible),
            )
            .values(phase="RUNNING", started_at=now, updated_at=now)
            .returning(AttemptRow)
        )
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return _snapshot(row) if row is not None else None

    async def persist_result(
        self,
        attempt_key: str,
        work_key: str,
        *,
        phase: str,
        report: dict[str, Any],
    ) -> Attempt | None:
        sid = self._uuid_or_none(attempt_key)
        if sid is None:
            return None
        now = datetime.now(timezone.utc)
        statement = (
            update(AttemptRow)
            .where(
                AttemptRow.key == sid,
                AttemptRow.work_key == work_key,
                AttemptRow.phase.not_in(TERMINAL_STATUSES),
            )
            .values(phase=phase, report=report, finished_at=now, updated_at=now)
            .returning(AttemptRow)
        )
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return _snapshot(row) if row is not None else None

    async def reset_after_worker_failure(self, attempt_key: str, work_key: str, message: str) -> None:
        sid = self._uuid_or_none(attempt_key)
        if sid is None:
            return
        await self._session.execute(
            update(AttemptRow)
            .where(
                AttemptRow.key == sid,
                AttemptRow.work_key == work_key,
                AttemptRow.phase == "RUNNING",
            )
            .values(
                phase="QUEUED",
                report={"firstFailureMessage": message[:2000]},
                updated_at=datetime.now(timezone.utc),
            )
        )

    @staticmethod
    def _uuid_or_none(value: str) -> uuid.UUID | None:
        try:
            return uuid.UUID(value)
        except (ValueError, TypeError, AttributeError):
            return None
