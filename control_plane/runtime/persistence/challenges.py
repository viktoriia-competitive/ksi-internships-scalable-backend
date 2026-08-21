from __future__ import annotations

import math

from sqlalchemy import String, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from control_plane.runtime.storage.models import ChallengeRow
from control_plane.runtime.core.entities import Challenge, PageSlice


def _snapshot(row: ChallengeRow) -> Challenge:
    return Challenge(
        key=row.key,
        short_code=row.short_code,
        name=row.name,
        level=row.level,
        score=row.score,
        accepted_count=int(row.accepted_count or 0),
        mode=row.mode,
        labels=list(row.labels or []),
        runtimes=list(row.runtimes or []),
        budget=dict(row.budget or {}),
        profile=dict(row.profile or {}),
    )


class ChallengeRepository:
    """PostgreSQL adapter for the challenge catalogue port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, challenge_key: str) -> Challenge | None:
        row = await self._session.get(ChallengeRow, challenge_key)
        return _snapshot(row) if row is not None else None

    async def page(
        self,
        *,
        search: str,
        level: str,
        label: str,
        mode: str,
        order_by: str,
        direction: str,
        index: int,
        size: int,
    ) -> PageSlice[Challenge]:
        size = min(max(int(size), 1), 100)
        requested_page = max(int(index), 1)
        predicates = self._filters(search=search, level=level, label=label, mode=mode)

        count_query = select(func.count()).select_from(ChallengeRow)
        if predicates:
            count_query = count_query.where(*predicates)
        total = int(await self._session.scalar(count_query) or 0)
        pages = max(1, math.ceil(total / size))
        current = min(requested_page, pages)

        primary_sort = self._sort_expression(order_by)
        primary_sort = primary_sort.desc() if direction.casefold() == "desc" else primary_sort.asc()
        query = select(ChallengeRow)
        if predicates:
            query = query.where(*predicates)
        query = (
            query.order_by(primary_sort, ChallengeRow.key.asc())
            .offset((current - 1) * size)
            .limit(size)
        )
        rows = list((await self._session.scalars(query)).all())
        return PageSlice(
            entries=[_snapshot(row) for row in rows],
            total_entries=total,
            index=current,
            size=size,
            total_pages=pages,
        )

    async def increment_accepted(self, challenge_key: str) -> None:
        row = await self._session.get(ChallengeRow, challenge_key, with_for_update=True)
        if row is not None:
            row.accepted_count = int(row.accepted_count or 0) + 1

    @staticmethod
    def _filters(*, search: str, level: str, label: str, mode: str):
        predicates = []
        if level and level != "all":
            predicates.append(ChallengeRow.level == level)
        if mode and mode != "all":
            predicates.append(ChallengeRow.mode == mode)
        if label and label != "all":
            predicates.append(ChallengeRow.labels.contains([label]))
        text = search.strip()
        if text:
            pattern = f"%{text}%"
            predicates.append(
                or_(
                    ChallengeRow.key.ilike(pattern),
                    ChallengeRow.short_code.ilike(pattern),
                    ChallengeRow.name.ilike(pattern),
                    ChallengeRow.mode.ilike(pattern),
                    cast(ChallengeRow.labels, String).ilike(pattern),
                )
            )
        return predicates

    @staticmethod
    def _sort_expression(order_by: str):
        difficulty_rank = case(
            (ChallengeRow.level == "easy", 0),
            (ChallengeRow.level == "medium", 1),
            (ChallengeRow.level == "hard", 2),
            else_=3,
        )
        return {
            "shortCode": ChallengeRow.short_code,
            "name": ChallengeRow.name,
            "level": difficulty_rank,
            "acceptedCount": ChallengeRow.accepted_count,
            "key": ChallengeRow.key,
            "score": ChallengeRow.score,
            "mode": ChallengeRow.mode,
        }.get(order_by, ChallengeRow.short_code)
