from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from control_plane.runtime.storage.models import (
    LifecycleEventRow,
    ProcessedCommandRow,
    AttemptProjectionRow,
    AttemptRow,
)
from control_plane.runtime.core.lifecycle import LifecycleEvent, AttemptProjection, evolve


class LifecycleRepository:
    """Append-only execution facts plus a rebuildable current-state projection."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(
        self,
        *,
        attempt_key: str,
        run_key: str,
        delivery_key: str,
        event_type: str,
        dedupe_key: str,
        payload: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> LifecycleEvent:
        existing = await self.session.scalar(
            select(LifecycleEventRow).where(LifecycleEventRow.dedupe_key == dedupe_key)
        )
        if existing is not None:
            return self._event(existing)

        sid = uuid.UUID(attempt_key)
        # Locking the aggregate row serializes sequence allocation across workers.
        attempt = await self.session.get(AttemptRow, sid, with_for_update=True)
        if attempt is None:
            raise ValueError(f"attempt does not exist: {attempt_key}")
        # A concurrent duplicate may have committed while we waited for the
        # aggregate lock. Re-check under the lock before allocating sequence.
        existing = await self.session.scalar(
            select(LifecycleEventRow).where(LifecycleEventRow.dedupe_key == dedupe_key)
        )
        if existing is not None:
            return self._event(existing)

        last_sequence = int(
            await self.session.scalar(
                select(func.coalesce(func.max(LifecycleEventRow.sequence), 0)).where(
                    LifecycleEventRow.attempt_key == sid
                )
            )
            or 0
        )
        event = LifecycleEventRow(
            attempt_key=sid,
            run_key=run_key,
            delivery_key=delivery_key,
            sequence=last_sequence + 1,
            event_type=event_type,
            dedupe_key=dedupe_key,
            payload=dict(payload or {}),
            occurred_at=occurred_at or datetime.now(timezone.utc),
        )
        self.session.add(event)
        await self.session.flush()
        await self._apply(event)
        return self._event(event)

    async def list_for_attempt(self, attempt_key: str) -> list[LifecycleEvent]:
        try:
            sid = uuid.UUID(attempt_key)
        except (ValueError, TypeError):
            return []
        rows = list(
            (
                await self.session.scalars(
                    select(LifecycleEventRow)
                    .where(LifecycleEventRow.attempt_key == sid)
                    .order_by(LifecycleEventRow.sequence.asc())
                )
            ).all()
        )
        return [self._event(row) for row in rows]

    async def rebuild_projection(self, attempt_key: str) -> AttemptProjection | None:
        try:
            sid = uuid.UUID(attempt_key)
        except (ValueError, TypeError):
            return None
        events = await self.list_for_attempt(attempt_key)
        if not events:
            return None
        current = AttemptProjection(attempt_key=attempt_key)
        for event in events:
            current = evolve(current, event)
        row = await self.session.get(AttemptProjectionRow, sid)
        if row is None:
            row = AttemptProjectionRow(attempt_key=sid)
            self.session.add(row)
        self._write_projection(row, current)
        await self.session.flush()
        return current

    async def _apply(self, row: LifecycleEventRow) -> None:
        projection_row = await self.session.get(
            AttemptProjectionRow, row.attempt_key, with_for_update=True
        )
        if projection_row is None:
            projection_row = AttemptProjectionRow(attempt_key=row.attempt_key)
            self.session.add(projection_row)
            await self.session.flush()
        current = AttemptProjection(
            attempt_key=str(projection_row.attempt_key),
            phase=projection_row.phase,
            verdict=projection_row.verdict,
            report=dict(projection_row.report or {}),
            retry_index=projection_row.retry_index,
            run_key=projection_row.run_key,
            last_sequence=projection_row.last_sequence,
            started_at=projection_row.started_at,
            finished_at=projection_row.finished_at,
            last_infrastructure_error=projection_row.last_infrastructure_error,
        )
        projected = evolve(current, self._event(row))
        self._write_projection(projection_row, projected)

    @staticmethod
    def _write_projection(row: AttemptProjectionRow, projected: AttemptProjection) -> None:
        row.phase = projected.phase
        row.verdict = projected.verdict
        row.report = dict(projected.report)
        row.retry_index = projected.retry_index
        row.run_key = projected.run_key
        row.last_sequence = projected.last_sequence
        row.started_at = projected.started_at
        row.finished_at = projected.finished_at
        row.last_infrastructure_error = projected.last_infrastructure_error
        row.updated_at = datetime.now(timezone.utc)

    @staticmethod
    def _event(row: LifecycleEventRow) -> LifecycleEvent:
        return LifecycleEvent(
            attempt_key=str(row.attempt_key),
            run_key=row.run_key,
            delivery_key=row.delivery_key,
            sequence=row.sequence,
            event_type=row.event_type,
            payload=dict(row.payload or {}),
            occurred_at=row.occurred_at,
        )


class ProcessedCommandRepository:
    """Database-side idempotency boundary for at-least-once stream delivery."""

    def __init__(self, session: AsyncSession, consumer: str = "evaluation-worker") -> None:
        self.session = session
        self.consumer = consumer

    async def contains(self, delivery_key: str) -> bool:
        row = await self.session.get(ProcessedCommandRow, (self.consumer, delivery_key))
        return row is not None

    async def mark(self, delivery_key: str) -> None:
        if not await self.contains(delivery_key):
            self.session.add(ProcessedCommandRow(consumer=self.consumer, delivery_key=delivery_key))
            await self.session.flush()
