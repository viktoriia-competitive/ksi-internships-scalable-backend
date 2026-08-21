from __future__ import annotations

from control_plane.runtime.use_cases.commands import ChallengeQuery
from control_plane.runtime.use_cases.errors import NotFoundError
from control_plane.runtime.use_cases.ports import ChallengeCatalog
from control_plane.runtime.core.entities import Challenge, PageSlice


class ChallengeService:
    def __init__(self, catalog: ChallengeCatalog) -> None:
        self._catalog = catalog

    async def list(self, query: ChallengeQuery) -> PageSlice[Challenge]:
        return await self._catalog.page(
            search=query.search,
            level=query.level,
            label=query.label,
            mode=query.mode,
            order_by=query.order_by,
            direction=query.direction,
            index=query.index,
            size=query.size,
        )

    async def require(self, challenge_key: str) -> Challenge:
        challenge = await self._catalog.get(challenge_key)
        if challenge is None:
            raise NotFoundError("challenge not found")
        return challenge
