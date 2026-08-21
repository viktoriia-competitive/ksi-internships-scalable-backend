from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from sqlalchemy import select

from control_plane.runtime.storage.models import ChallengeRow
from control_plane.runtime.storage.session import Database
from control_plane.runtime.persistence.revisions import ChallengeRevisionRepository
from control_plane.runtime.persistence.accounts import AccountRepository
from control_plane.runtime.seed.package_catalog import discover_bundles, load_challenge_bundle
from control_plane.runtime.settings import REPO_ROOT, get_settings
from control_plane.runtime.storage.bundle_archive import snapshot_bundle


async def seed(challenges_root: Path) -> int:
    settings = get_settings()
    db = Database(settings.database_url)
    await db.create_schema()
    bundles = discover_bundles(challenges_root)
    async with db.sessions() as session:
        for bundle_dir in bundles:
            item = load_challenge_bundle(bundle_dir, REPO_ROOT)
            row = await session.get(ChallengeRow, item.key)
            if row is None:
                row = ChallengeRow(
                    key=item.key,
                    short_code=item.short_code,
                    name=item.name,
                    budget=item.budget,
                )
                session.add(row)
            row.short_code = item.short_code
            row.name = item.name
            row.level = item.level
            row.score = item.score
            row.accepted_count = item.accepted_count
            row.mode = item.mode
            row.labels = item.labels
            row.runtimes = item.runtimes
            row.budget = item.budget
            row.profile = item.profile
            await session.flush()

            digest, artifact_dir, manifest = snapshot_bundle(
                bundle_dir,
                REPO_ROOT / "challenge_bank" / ".runline" / "revisions",
            )
            revision = await ChallengeRevisionRepository(session).ensure(
                challenge_key=item.key,
                bundle_digest=digest,
                artifact_ref=artifact_dir.relative_to(REPO_ROOT).as_posix(),
                manifest=manifest,
            )
            row.profile = {
                **item.profile,
                "revision": {
                    "id": revision.id,
                    "number": revision.revision,
                    "bundleDigest": revision.bundle_digest,
                },
            }
        await AccountRepository(session).get_or_create(settings.dev_handle)
        await session.commit()
    await db.close()
    print(f"seeded {len(bundles)} challenge bundles and immutable revisions into PostgreSQL")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed PostgreSQL from the challenge bank")
    parser.add_argument(
        "--challenges-root",
        type=Path,
        default=REPO_ROOT / "challenge_bank" / "challenges",
    )
    args = parser.parse_args()
    return asyncio.run(seed(args.challenges_root))


if __name__ == "__main__":
    raise SystemExit(main())
