from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from control_plane.runtime.storage.models import AttemptRow
from control_plane.runtime.storage.session import Database
from control_plane.runtime.persistence.lifecycle import LifecycleRepository
from control_plane.runtime.settings import get_settings


async def rebuild(attempt_key: str | None = None) -> int:
    settings = get_settings()
    db = Database(settings.database_url)
    await db.create_schema()
    count = 0
    async with db.sessions() as session:
        events = LifecycleRepository(session)
        if attempt_key:
            projection = await events.rebuild_projection(attempt_key)
            count = 1 if projection is not None else 0
        else:
            keys = list((await session.scalars(select(AttemptRow.key))).all())
            for key in keys:
                if await events.rebuild_projection(str(key)) is not None:
                    count += 1
        await session.commit()
    await db.close()
    print(f"rebuilt {count} attempt projections from lifecycle_events")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild disposable attempt projections")
    parser.add_argument("--attempt-key")
    args = parser.parse_args()
    asyncio.run(rebuild(args.attempt_key))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
