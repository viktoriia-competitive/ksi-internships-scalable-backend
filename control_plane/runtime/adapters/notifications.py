from __future__ import annotations

import json

from redis.asyncio import Redis


class ResultPublisher:
    def __init__(self, redis: Redis, channel: str) -> None:
        self.redis = redis
        self.channel = channel

    async def publish_attempt(self, attempt_key: str, status: str) -> None:
        await self.redis.publish(
            self.channel,
            json.dumps({"attemptKey": attempt_key, "phase": status}, separators=(",", ":")),
        )
