from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from control_plane.runtime.core.evaluation_command import EvaluationCommand


@dataclass(frozen=True, slots=True)
class ClaimedCommand:
    stream: str
    message_id: str
    command: EvaluationCommand


class ExecutionQueue(Protocol):
    async def enqueue(self, command: EvaluationCommand) -> None: ...
    async def reserve(self, consumer: str, block_ms: int = 1000) -> ClaimedCommand | None: ...
    async def ack(self, reserved: ClaimedCommand) -> None: ...
    async def retry_or_dead_letter(
        self,
        reserved: ClaimedCommand,
        error: str,
        *,
        retry_command: EvaluationCommand | None = None,
    ) -> bool: ...
