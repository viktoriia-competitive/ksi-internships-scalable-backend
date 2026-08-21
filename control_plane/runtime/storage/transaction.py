from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from control_plane.runtime.use_cases.errors import TransactionConflict


class SqlAlchemyTransaction:
    """Translate SQLAlchemy transaction failures into application-level errors."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as exc:
            raise TransactionConflict("database uniqueness conflict") from exc

    async def rollback(self) -> None:
        await self._session.rollback()
