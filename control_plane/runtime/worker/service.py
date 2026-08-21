from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from control_plane.runtime.storage.session import Database
from control_plane.runtime.core.evaluation_command import EvaluationCommand
from control_plane.runtime.core.lifecycle import (
    EXECUTION_CLAIMED,
    EXECUTION_COMPLETED,
    EXECUTION_REQUESTED,
    EXECUTION_RETRYABLE_FAILURE,
    EXECUTION_TERMINAL_FAILURE,
)
from control_plane.runtime.adapters.notifications import ResultPublisher
from control_plane.runtime.adapters.queue import ClaimedCommand
from control_plane.runtime.adapters.redis_queue import RedisExecutionQueue
from control_plane.runtime.persistence.lifecycle import LifecycleRepository, ProcessedCommandRepository
from control_plane.runtime.persistence.outbox import OutboxRepository
from control_plane.runtime.persistence.challenges import ChallengeRepository
from control_plane.runtime.persistence.attempts import AttemptRepository
from control_plane.runtime.persistence.accounts import AccountRepository
from control_plane.runtime.storage.sources import materialized_artifact
from control_plane.runtime.worker.evaluation_report import build_evaluation_report
from execution_engine.core.engine import evaluate_bundle

log = logging.getLogger("runline.worker")


class EvaluationWorker:
    """At-least-once command consumer with a database idempotency boundary.

    Redis owns delivery, PostgreSQL owns facts. A command is marked processed in
    the same transaction as its terminal execution event, so redelivery after a
    crash is harmless from the application's point of view.
    """

    def __init__(
        self,
        *,
        db: Database,
        queue: RedisExecutionQueue,
        publisher: ResultPublisher,
        challenges_root: Path,
        challenge_artifacts_root: Path,
        use_cgroup: bool,
        max_attempts: int,
    ) -> None:
        self.db = db
        self.queue = queue
        self.publisher = publisher
        self.challenges_root = challenges_root
        self.challenge_artifacts_root = challenge_artifacts_root
        self.use_cgroup = use_cgroup
        self.max_attempts = max_attempts

    async def dispatch_outbox(self, batch_size: int = 100) -> int:
        published = 0
        async with self.db.sessions() as session:
            repo = OutboxRepository(session)
            rows = await repo.next_batch(batch_size)
            for row in rows:
                try:
                    command = EvaluationCommand.decode(row.payload["command"])
                    await self.queue.enqueue(command)
                    repo.mark_published(row)
                    published += 1
                except Exception as exc:
                    repo.mark_failure(row, str(exc))
                    log.warning("outbox dispatch failed id=%s: %s", row.id, exc)
                    break
            await session.commit()
        return published

    async def process(self, reserved: ClaimedCommand, *, reclaimed: bool = False) -> None:
        if await self._already_processed(reserved.command.delivery_key):
            await self.queue.ack(reserved)
            return

        row = await self._claim(reserved, reclaimed=reclaimed)
        if row is None:
            # A terminal state or an obsolete duplicate. If the
            # terminal transaction committed, processed_commands catches it on
            # the next delivery; otherwise there is no safe work to claim here.
            await self.queue.ack(reserved)
            return

        try:
            bundle_dir = self._bundle_for(reserved.command)
            with materialized_artifact(row.source_text, row.artifact_name) as source_path:
                suite = await asyncio.to_thread(
                    evaluate_bundle,
                    bundle_dir,
                    source_path,
                    runtime=reserved.command.runtime,
                    run_key=reserved.command.run_key,
                    use_cgroup=self.use_cgroup,
                )
            payload = build_evaluation_report(suite)
            await self._store_success(reserved, row.account_key, suite.status.value, payload)
            await self.queue.ack(reserved)
            try:
                await self.publisher.publish_attempt(reserved.command.attempt_key, suite.status.value)
            except Exception:
                log.exception("result publish failed for %s", reserved.command.work_key)
        except Exception as exc:
            log.exception("execution failed job=%s command=%s", reserved.command.work_key, reserved.command.delivery_key)
            dead = reserved.command.retry_index + 1 >= self.max_attempts
            retry_command = None
            if dead:
                await self._store_terminal_failure(reserved, str(exc))
            else:
                retry_command = reserved.command.retry()
                await self._reset_for_retry(reserved, retry_command, str(exc))
            await self.queue.retry_or_dead_letter(reserved, str(exc), retry_command=retry_command)

    def _bundle_for(self, command: EvaluationCommand) -> Path:
        if not command.challenge_digest:
            return self.challenges_root / command.challenge_key
        immutable = self.challenge_artifacts_root / command.challenge_digest
        if not immutable.is_dir():
            raise FileNotFoundError(
                f"immutable challenge revision is unavailable: {command.challenge_digest}"
            )
        return immutable

    async def _already_processed(self, delivery_key: str) -> bool:
        async with self.db.sessions() as session:
            return await ProcessedCommandRepository(session).contains(delivery_key)

    async def _claim(self, reserved: ClaimedCommand, *, reclaimed: bool):
        async with self.db.sessions() as session:
            repo = AttemptRepository(session)
            row = await repo.claim_for_execution(
                reserved.command.attempt_key,
                reserved.command.work_key,
                allow_running=reclaimed,
            )
            if row is not None:
                await LifecycleRepository(session).append(
                    attempt_key=reserved.command.attempt_key,
                    run_key=reserved.command.run_key,
                    delivery_key=reserved.command.delivery_key,
                    event_type=EXECUTION_CLAIMED,
                    dedupe_key=f"{reserved.command.delivery_key}:claimed",
                    payload={"retryIndex": reserved.command.retry_index},
                )
            await session.commit()
            return row

    async def _store_success(self, reserved: ClaimedCommand, account_key, status: str, payload: dict) -> None:
        async with self.db.sessions() as session:
            processed = ProcessedCommandRepository(session)
            if await processed.contains(reserved.command.delivery_key):
                return
            events = LifecycleRepository(session)
            await events.append(
                attempt_key=reserved.command.attempt_key,
                run_key=reserved.command.run_key,
                delivery_key=reserved.command.delivery_key,
                event_type=EXECUTION_COMPLETED,
                dedupe_key=f"{reserved.command.delivery_key}:completed",
                payload={"verdict": status, "report": payload},
            )
            attempts = AttemptRepository(session)
            row = await attempts.persist_result(
                reserved.command.attempt_key,
                reserved.command.work_key,
                phase=status,
                report=payload,
            )
            if row is not None and status == "ACCEPTED":
                accounts = AccountRepository(session)
                if await accounts.record_challenge_completion(account_key, row.challenge_key):
                    await ChallengeRepository(session).increment_accepted(row.challenge_key)
            await processed.mark(reserved.command.delivery_key)
            await session.commit()

    async def _reset_for_retry(self, reserved: ClaimedCommand, retry_command: EvaluationCommand, message: str) -> None:
        async with self.db.sessions() as session:
            events = LifecycleRepository(session)
            await events.append(
                attempt_key=reserved.command.attempt_key,
                run_key=reserved.command.run_key,
                delivery_key=reserved.command.delivery_key,
                event_type=EXECUTION_RETRYABLE_FAILURE,
                dedupe_key=f"{reserved.command.delivery_key}:retryable-failure",
                payload={
                    "message": message[:2000],
                    "retryIndex": reserved.command.retry_index,
                    "nextRetryIndex": retry_command.retry_index,
                },
            )
            await events.append(
                attempt_key=retry_command.attempt_key,
                run_key=retry_command.run_key,
                delivery_key=retry_command.delivery_key,
                event_type=EXECUTION_REQUESTED,
                dedupe_key=f"{retry_command.delivery_key}:requested",
                payload={"retryIndex": retry_command.retry_index, "retryOf": reserved.command.run_key},
            )
            await AttemptRepository(session).reset_after_worker_failure(
                reserved.command.attempt_key,
                reserved.command.work_key,
                message,
            )
            await session.commit()

    async def _store_terminal_failure(self, reserved: ClaimedCommand, message: str) -> None:
        payload = {
            "testsPassed": 0,
            "testsTotal": 0,
            "maxCpuMs": 0,
            "maxMemKb": 0,
            "compileMessage": "",
            "firstFailureMessage": message[:4000],
            "failure": None,
            "perTest": [],
        }
        async with self.db.sessions() as session:
            processed = ProcessedCommandRepository(session)
            if await processed.contains(reserved.command.delivery_key):
                return
            await LifecycleRepository(session).append(
                attempt_key=reserved.command.attempt_key,
                run_key=reserved.command.run_key,
                delivery_key=reserved.command.delivery_key,
                event_type=EXECUTION_TERMINAL_FAILURE,
                dedupe_key=f"{reserved.command.delivery_key}:terminal-failure",
                payload={"message": message[:2000], "report": payload},
            )
            await AttemptRepository(session).persist_result(
                reserved.command.attempt_key,
                reserved.command.work_key,
                phase="INTERNAL_ERROR",
                report=payload,
            )
            await processed.mark(reserved.command.delivery_key)
            await session.commit()
