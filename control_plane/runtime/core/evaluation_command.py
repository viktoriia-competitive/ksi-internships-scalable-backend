from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from enum import Enum


class WorkClass(str, Enum):
    INTERACTIVE = "interactive"
    EVALUATION = "evaluation"


@dataclass(frozen=True, slots=True)
class EvaluationCommand:
    work_key: str
    attempt_key: str
    challenge_key: str
    runtime: str
    priority: WorkClass = WorkClass.EVALUATION
    retry_index: int = 0
    delivery_key: str = ""
    run_key: str = ""
    challenge_revision_key: str | None = None
    challenge_digest: str | None = None

    def __post_init__(self) -> None:
        # Deterministic fallbacks keep a command stable across a retry decision.
        if not self.delivery_key:
            object.__setattr__(
                self,
                "delivery_key",
                str(uuid.uuid5(uuid.NAMESPACE_URL, f"runline:command:{self.work_key}:{self.retry_index}")),
            )
        if not self.run_key:
            object.__setattr__(
                self,
                "run_key",
                str(uuid.uuid5(uuid.NAMESPACE_URL, f"runline:execution:{self.work_key}:{self.retry_index}")),
            )

    def encode(self) -> str:
        payload = asdict(self)
        payload["priority"] = self.priority.value
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)

    @classmethod
    def decode(cls, raw: str | bytes) -> "EvaluationCommand":
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        data["priority"] = WorkClass(data.get("priority", "evaluation"))
        return cls(**data)

    def retry(self) -> "EvaluationCommand":
        next_attempt = self.retry_index + 1
        return EvaluationCommand(
            work_key=self.work_key,
            attempt_key=self.attempt_key,
            challenge_key=self.challenge_key,
            runtime=self.runtime,
            priority=self.priority,
            retry_index=next_attempt,
            delivery_key=str(uuid.uuid5(uuid.NAMESPACE_URL, f"runline:retry-command:{self.delivery_key}:{next_attempt}")),
            run_key=str(uuid.uuid5(uuid.NAMESPACE_URL, f"runline:retry-execution:{self.run_key}:{next_attempt}")),
            challenge_revision_key=self.challenge_revision_key,
            challenge_digest=self.challenge_digest,
        )
