from __future__ import annotations

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from control_plane.runtime.core.evaluation_command import EvaluationCommand, WorkClass
from control_plane.runtime.adapters.queue import ClaimedCommand


class RedisExecutionQueue:
    """Interactive work is checked before full evaluation work."""

    def __init__(self, redis: Redis, *, namespace: str, group: str, max_attempts: int, visibility_timeout_ms: int) -> None:
        self.redis = redis
        self.group = group
        self.max_attempts = max_attempts
        self.visibility_timeout_ms = visibility_timeout_ms
        self.interactive_stream = f"{namespace}:work:interactive"
        self.evaluation_stream = f"{namespace}:work:evaluation"
        self.dead_stream = f"{namespace}:work:dead"
        self._groups_ready = False

    async def _ensure_groups(self) -> None:
        if self._groups_ready:
            return
        for stream in (self.interactive_stream, self.evaluation_stream):
            try:
                await self.redis.xgroup_create(stream, self.group, id="0", mkstream=True)
            except ResponseError as exc:
                if "BUSYGROUP" not in str(exc):
                    raise
        self._groups_ready = True

    def _stream_for(self, priority: WorkClass) -> str:
        return self.interactive_stream if priority is WorkClass.INTERACTIVE else self.evaluation_stream

    async def enqueue(self, command: EvaluationCommand) -> None:
        await self._ensure_groups()
        await self.redis.xadd(
            self._stream_for(command.priority),
            {"command": command.encode()},
            maxlen=100_000,
            approximate=True,
        )

    async def reserve(self, consumer: str, block_ms: int = 1000) -> ClaimedCommand | None:
        await self._ensure_groups()
        for stream, block in ((self.interactive_stream, 1), (self.evaluation_stream, block_ms)):
            rows = await self.redis.xreadgroup(
                self.group,
                consumer,
                {stream: ">"},
                count=1,
                block=block,
            )
            if rows:
                _, messages = rows[0]
                message_id, fields = messages[0]
                raw = fields.get(b"command") or fields.get("command")
                if raw is None:
                    await self.redis.xack(stream, self.group, message_id)
                    continue
                return ClaimedCommand(
                    stream=stream,
                    message_id=self._decode(message_id),
                    command=EvaluationCommand.decode(raw),
                )
        return None

    async def ack(self, reserved: ClaimedCommand) -> None:
        await self.redis.xack(reserved.stream, self.group, reserved.message_id)

    async def retry_or_dead_letter(
        self,
        reserved: ClaimedCommand,
        error: str,
        *,
        retry_command: EvaluationCommand | None = None,
    ) -> bool:
        next_attempt = reserved.command.retry_index + 1
        if next_attempt >= self.max_attempts:
            # Publish before ACK. If Redis fails here the original pending entry
            # remains reclaimable; if ACK fails after publish, duplicate handling
            # at the persistence boundary keeps a redelivery harmless.
            await self.redis.xadd(
                self.dead_stream,
                {"command": reserved.command.encode(), "error": error[:2000]},
                maxlen=10_000,
                approximate=True,
            )
            await self.ack(reserved)
            return True
        command = retry_command or reserved.command.retry()
        await self.enqueue(command)
        await self.ack(reserved)
        return False

    async def reclaim_stale(self, consumer: str) -> list[ClaimedCommand]:
        await self._ensure_groups()
        reclaimed: list[ClaimedCommand] = []
        for stream in (self.interactive_stream, self.evaluation_stream):
            start = "0-0"
            while True:
                result = await self.redis.xautoclaim(
                    stream,
                    self.group,
                    consumer,
                    min_idle_time=self.visibility_timeout_ms,
                    start_id=start,
                    count=10,
                )
                start, messages = result[0], result[1]
                for message_id, fields in messages:
                    raw = fields.get(b"command") or fields.get("command")
                    if raw is not None:
                        reclaimed.append(
                            ClaimedCommand(
                                stream=stream,
                                message_id=self._decode(message_id),
                                command=EvaluationCommand.decode(raw),
                            )
                        )
                if not messages or self._decode(start) == "0-0":
                    break
        return reclaimed

    async def close(self) -> None:
        await self.redis.aclose()

    @staticmethod
    def _decode(value: str | bytes) -> str:
        return value.decode("utf-8") if isinstance(value, bytes) else str(value)
