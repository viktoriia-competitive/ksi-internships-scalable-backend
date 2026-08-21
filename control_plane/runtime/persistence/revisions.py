from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from control_plane.runtime.storage.models import ChallengeRevisionRow


@dataclass(frozen=True, slots=True)
class ChallengeRevision:
    id: str
    challenge_key: str
    revision: int
    bundle_digest: str
    artifact_ref: str
    manifest: dict


class ChallengeRevisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def latest(self, challenge_key: str) -> ChallengeRevision | None:
        row = await self.session.scalar(
            select(ChallengeRevisionRow)
            .where(ChallengeRevisionRow.challenge_key == challenge_key)
            .order_by(ChallengeRevisionRow.revision.desc())
            .limit(1)
        )
        return self._snapshot(row) if row else None

    async def ensure(
        self,
        *,
        challenge_key: str,
        bundle_digest: str,
        artifact_ref: str,
        manifest: dict,
    ) -> ChallengeRevision:
        existing = await self.session.scalar(
            select(ChallengeRevisionRow).where(
                ChallengeRevisionRow.challenge_key == challenge_key,
                ChallengeRevisionRow.bundle_digest == bundle_digest,
            )
        )
        if existing is not None:
            return self._snapshot(existing)
        last = int(
            await self.session.scalar(
                select(func.coalesce(func.max(ChallengeRevisionRow.revision), 0)).where(
                    ChallengeRevisionRow.challenge_key == challenge_key
                )
            )
            or 0
        )
        row = ChallengeRevisionRow(
            challenge_key=challenge_key,
            revision=last + 1,
            bundle_digest=bundle_digest,
            artifact_ref=artifact_ref,
            manifest=dict(manifest),
        )
        self.session.add(row)
        await self.session.flush()
        return self._snapshot(row)

    @staticmethod
    def _snapshot(row: ChallengeRevisionRow) -> ChallengeRevision:
        return ChallengeRevision(
            id=str(row.id),
            challenge_key=row.challenge_key,
            revision=row.revision,
            bundle_digest=row.bundle_digest,
            artifact_ref=row.artifact_ref,
            manifest=dict(row.manifest or {}),
        )
