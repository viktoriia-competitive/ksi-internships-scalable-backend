from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from control_plane.runtime.storage.models import CommandOutboxRow
from control_plane.runtime.core.evaluation_command import EvaluationCommand


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def stage(self, command: EvaluationCommand) -> CommandOutboxRow:
        row = CommandOutboxRow(
            aggregate_id=command.delivery_key,
            event_type="execution.requested",
            payload={"command": command.encode()},
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def next_batch(self, limit: int = 100) -> list[CommandOutboxRow]:
        stmt = (
            select(CommandOutboxRow)
            .where(CommandOutboxRow.published.is_(False))
            .order_by(CommandOutboxRow.id.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())

    def mark_published(self, row: CommandOutboxRow) -> None:
        row.published = True
        row.published_at = datetime.now(timezone.utc)
        row.last_error = None

    def mark_failure(self, row: CommandOutboxRow, error: str) -> None:
        row.attempts += 1
        row.last_error = error[:2000]
