from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import socket

from redis.asyncio import Redis

from control_plane.runtime.storage.session import Database
from control_plane.runtime.adapters.notifications import ResultPublisher
from control_plane.runtime.adapters.redis_queue import RedisExecutionQueue
from control_plane.runtime.settings import REPO_ROOT, get_settings
from control_plane.runtime.worker.service import EvaluationWorker

log = logging.getLogger("oj.worker")


async def run_worker(*, once: bool = False) -> int:
    settings = get_settings()
    db = Database(settings.database_url)
    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    queue = RedisExecutionQueue(
        redis,
        namespace=settings.queue_namespace,
        group=settings.queue_group,
        max_attempts=settings.queue_max_attempts,
        visibility_timeout_ms=settings.queue_visibility_timeout_ms,
    )
    worker = EvaluationWorker(
        db=db,
        queue=queue,
        publisher=ResultPublisher(redis, settings.result_channel),
        challenges_root=REPO_ROOT / "challenge_bank" / "challenges",
        challenge_artifacts_root=REPO_ROOT / "challenge_bank" / ".runline" / "revisions",
        use_cgroup=settings.execution_use_cgroup,
        max_attempts=settings.queue_max_attempts,
    )
    consumer = f"{socket.gethostname()}-{os.getpid()}"
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stopping.set)
        except NotImplementedError:
            pass

    processed = 0
    try:
        while not stopping.is_set():
            await worker.dispatch_outbox()
            reclaimed = await queue.reclaim_stale(consumer)
            for item in reclaimed:
                await worker.process(item, reclaimed=True)
                processed += 1
                if once:
                    return processed

            reserved = await queue.reserve(consumer, block_ms=1000)
            if reserved is None:
                if once:
                    return processed
                continue
            await worker.process(reserved)
            processed += 1
            if once:
                return processed
    finally:
        await redis.aclose()
        await db.close()
    return processed


def main() -> int:
    parser = argparse.ArgumentParser(description="Redis-backed evaluation worker")
    parser.add_argument("--once", action="store_true", help="process at most one queued execution")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    return 0 if asyncio.run(run_worker(once=args.once)) >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
