from __future__ import annotations

import uuid
from datetime import datetime, timezone

from control_plane.runtime.use_cases.commands import OpenAttemptCommand, AttemptQuery
from control_plane.runtime.use_cases.errors import NotFoundError, TransactionConflict, ValidationError
from control_plane.runtime.use_cases.ports import (
    ChallengeRevisionCatalog,
    LifecycleStore,
    EvaluationOutbox,
    ChallengeCatalog,
    AttemptStore,
    Transaction,
    AccountDirectory,
)
from control_plane.runtime.core.entities import Account, Attempt, NewAttempt, PageSlice
from control_plane.runtime.core.evaluation_command import EvaluationCommand, WorkClass
from control_plane.runtime.core.lifecycle import EXECUTION_REQUESTED, ATTEMPT_OPENED
from control_plane.runtime.storage.sources import artifact_metadata


class AttemptService:
    def __init__(
        self,
        transaction: Transaction,
        *,
        attempts: AttemptStore,
        challenges: ChallengeCatalog,
        accounts: AccountDirectory,
        outbox: EvaluationOutbox,
        dev_handle: str,
        events: LifecycleStore | None = None,
        revisions: ChallengeRevisionCatalog | None = None,
    ) -> None:
        self._transaction = transaction
        self._attempts = attempts
        self._challenges = challenges
        self._accounts = accounts
        self._outbox = outbox
        self._dev_handle = dev_handle
        self._events = events
        self._revisions = revisions

    async def create(
        self,
        command: OpenAttemptCommand,
        *,
        x_handle: str | None,
        x_account_key: str | None,
        request_key: str | None = None,
    ) -> Attempt:
        source = command.source_text
        if not source.strip():
            raise ValidationError("sourceText is empty")

        challenge = await self._challenges.get(command.challenge_key)
        if challenge is None:
            raise NotFoundError("challenge not found")

        runtime = self._normalize_runtime(command.runtime, challenge.runtimes)
        account = await self._resolve_account(x_handle=x_handle, x_account_key=x_account_key)
        key = self._normalize_request_key(request_key)
        if key is not None:
            existing = await self._attempts.get_by_request_key(account.key, key)
            if existing is not None:
                return existing

        attempt_key = uuid.uuid4()
        work_key = f"evaluate:{attempt_key}"
        metadata = artifact_metadata(
            runtime=runtime,
            source_text=source,
            artifact_name=command.artifact_name,
            media_type=command.media_type,
        )
        item = NewAttempt(
            key=attempt_key,
            account_key=account.key,
            actor_handle=account.handle,
            challenge_key=challenge.key,
            challenge_short_code=challenge.short_code,
            challenge_name=challenge.name,
            runtime=runtime,
            artifact_ref=f"sha256:{metadata.digest}",
            source_text=source,
            artifact_name=metadata.name,
            media_type=metadata.media_type,
            artifact_bytes=metadata.bytes,
            work_key=work_key,
            request_key=key,
            created_at=datetime.now(timezone.utc),
        )
        created = await self._attempts.add(item)
        revision = await self._revisions.latest(challenge.key) if self._revisions is not None else None
        evaluation = EvaluationCommand(
            work_key=work_key,
            attempt_key=str(attempt_key),
            challenge_key=challenge.key,
            runtime=runtime,
            priority=WorkClass.EVALUATION,
            delivery_key=str(uuid.uuid4()),
            run_key=str(uuid.uuid4()),
            challenge_revision_key=getattr(revision, "id", None),
            challenge_digest=getattr(revision, "bundle_digest", None),
        )
        if self._events is not None:
            await self._events.append(
                attempt_key=str(attempt_key),
                run_key=evaluation.run_key,
                delivery_key=evaluation.delivery_key,
                event_type=ATTEMPT_OPENED,
                dedupe_key=f"{evaluation.delivery_key}:attempt-opened",
                payload={
                    "challenge_key": challenge.key,
                    "runtime": runtime,
                    "artifact_digest": metadata.digest,
                    "challenge_revision_key": evaluation.challenge_revision_key,
                    "challenge_digest": evaluation.challenge_digest,
                },
            )
            await self._events.append(
                attempt_key=str(attempt_key),
                run_key=evaluation.run_key,
                delivery_key=evaluation.delivery_key,
                event_type=EXECUTION_REQUESTED,
                dedupe_key=f"{evaluation.delivery_key}:requested",
                payload={"retryIndex": 0},
            )
        await self._outbox.stage(evaluation)
        try:
            await self._transaction.commit()
            return created
        except TransactionConflict:
            await self._transaction.rollback()
            if key is not None:
                existing = await self._attempts.get_by_request_key(account.key, key)
                if existing is not None:
                    return existing
            raise

    async def get(self, attempt_key: str) -> Attempt:
        attempt = await self._attempts.get(attempt_key)
        if attempt is None:
            raise NotFoundError("attempt not found")
        return attempt

    async def list(self, query: AttemptQuery) -> PageSlice[Attempt]:
        try:
            return await self._attempts.page(
                index=query.index,
                size=query.size,
                challenge_key=query.challenge_key,
                phase=query.phase,
                actor_key=query.actor_key,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    async def _resolve_account(self, *, x_handle: str | None, x_account_key: str | None) -> Account:
        if x_account_key:
            account = await self._accounts.find_by_id(x_account_key)
            if account is not None:
                return account
        if x_handle:
            account = await self._accounts.find_by_handle(x_handle)
            if account is not None:
                return account
        return await self._accounts.get_or_create(self._dev_handle)

    @staticmethod
    def _normalize_request_key(value: str | None) -> str | None:
        if value is None:
            return None
        key = value.strip()
        if not key:
            return None
        if len(key) > 128:
            raise ValidationError("Idempotency-Key is too long")
        return key

    @staticmethod
    def _normalize_runtime(requested: str, allowed: list[str]) -> str:
        normalized = requested.strip()
        if not allowed:
            return normalized
        canonical = {item.casefold(): item for item in allowed}
        try:
            return canonical[normalized.casefold()]
        except KeyError as exc:
            raise ValidationError(
                f"runtime {normalized!r} is not enabled for this challenge; enabled={allowed}"
            ) from exc
