from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from control_plane.runtime.storage.models import AccountRow
from control_plane.runtime.core.entities import Account


def _snapshot(row: AccountRow) -> Account:
    return Account(
        key=row.key,
        handle=row.handle,
        accepted_count=int(row.accepted_count or 0),
        completed_challenge_keys=list(row.completed_challenge_keys or []),
    )


class AccountRepository:
    """Identity persistence adapter; no ORM objects leave this module."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, handle: str) -> Account:
        display = handle.strip()
        normalized = display.casefold()
        row = await self._session.scalar(
            select(AccountRow).where(AccountRow.handle_normalized == normalized)
        )
        if row is None:
            row = AccountRow(handle=display, handle_normalized=normalized)
            self._session.add(row)
            await self._session.flush()
        return _snapshot(row)

    async def find_by_id(self, account_key: str) -> Account | None:
        try:
            key = uuid.UUID(account_key)
        except ValueError:
            return None
        row = await self._session.get(AccountRow, key)
        return _snapshot(row) if row is not None else None

    async def find_by_handle(self, handle: str) -> Account | None:
        row = await self._session.scalar(
            select(AccountRow).where(AccountRow.handle_normalized == handle.strip().casefold())
        )
        return _snapshot(row) if row is not None else None

    async def record_challenge_completion(self, account_key: uuid.UUID, challenge_key: str) -> bool:
        row = await self._session.get(AccountRow, account_key, with_for_update=True)
        if row is None:
            return False
        completed = list(row.completed_challenge_keys or [])
        if challenge_key in completed:
            return False
        completed.append(challenge_key)
        row.completed_challenge_keys = completed
        row.accepted_count = len(completed)
        row.updated_at = datetime.now(timezone.utc)
        return True
