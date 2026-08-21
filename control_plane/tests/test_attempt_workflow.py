from __future__ import annotations

import asyncio
import uuid
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from control_plane.runtime.use_cases.commands import OpenAttemptCommand, AttemptQuery
from control_plane.runtime.use_cases.errors import NotFoundError, ValidationError
from control_plane.runtime.use_cases.attempts import AttemptService
from control_plane.runtime.core.entities import Account, Attempt, Challenge, NewAttempt, PageSlice


class FakeTransaction:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeChallenges:
    def __init__(self, challenge: Challenge | None) -> None:
        self.challenge = challenge

    async def get(self, challenge_key: str):
        return self.challenge if self.challenge and self.challenge.key == challenge_key else None

    async def page(self, **query):
        return PageSlice([], 0, 1, query.get("size", 50), 1)

    async def increment_accepted(self, challenge_key: str) -> None:
        return None


class FakeAccounts:
    def __init__(self, account: Account) -> None:
        self.account = account

    async def get_or_create(self, handle: str):
        return self.account

    async def find_by_id(self, account_key: str):
        return self.account if str(self.account.key) == account_key else None

    async def find_by_handle(self, handle: str):
        return self.account if self.account.handle.casefold() == handle.casefold() else None

    async def record_challenge_completion(self, account_key, challenge_key: str) -> bool:
        return True


class FakeAttempts:
    def __init__(self) -> None:
        self.items: dict[str, Attempt] = {}
        self.by_key: dict[tuple[uuid.UUID, str], Attempt] = {}

    async def add(self, item: NewAttempt) -> Attempt:
        attempt = Attempt(
            key=item.key,
            account_key=item.account_key,
            actor_handle=item.actor_handle,
            challenge_key=item.challenge_key,
            challenge_short_code=item.challenge_short_code,
            challenge_name=item.challenge_name,
            runtime=item.runtime,
            phase=item.phase,
            artifact_ref=item.artifact_ref,
            source_text=item.source_text,
            artifact_name=item.artifact_name,
            media_type=item.media_type,
            artifact_bytes=item.artifact_bytes,
            report=item.report,
            work_key=item.work_key,
            request_key=item.request_key,
            created_at=item.created_at,
        )
        self.items[str(attempt.key)] = attempt
        if attempt.request_key:
            self.by_key[(attempt.account_key, attempt.request_key)] = attempt
        return attempt

    async def get(self, attempt_key: str):
        return self.items.get(attempt_key)

    async def get_by_request_key(self, account_key: uuid.UUID, key: str):
        return self.by_key.get((account_key, key))

    async def page(self, **query):
        entries = list(self.items.values())
        return PageSlice(entries, len(entries), 1, query["size"], 1)


class FakeOutbox:
    def __init__(self) -> None:
        self.jobs = []

    async def stage(self, job):
        self.jobs.append(job)
        return object()


def challenge() -> Challenge:
    return Challenge(
        key="demo-1",
        short_code="DEMO-1",
        name="Demo",
        level="easy",
        score=None,
        accepted_count=0,
        mode="stdio",
        labels=["intro"],
        runtimes=["Python", "C++"],
        budget={"cpuMillis": 1000, "memoryMiB": 64},
        profile={},
    )


def account() -> Account:
    return Account(uuid.uuid4(), "developer", 0, [])


def service(*, available_challenge: Challenge | None = None):
    tx = FakeTransaction()
    attempts = FakeAttempts()
    outbox = FakeOutbox()
    svc = AttemptService(
        tx,
        attempts=attempts,
        challenges=FakeChallenges(available_challenge if available_challenge is not None else challenge()),
        accounts=FakeAccounts(account()),
        outbox=outbox,
        dev_handle="developer",
    )
    return svc, tx, attempts, outbox


def run(coro):
    return asyncio.run(coro)


def test_open_attempt_is_atomic_with_execution_request() -> None:
    svc, tx, attempts, outbox = service()
    created = run(
        svc.create(
            OpenAttemptCommand("demo-1", "python", "print(42)\n", "solution.py"),
            x_handle=None,
            x_account_key=None,
            request_key="request-123",
        )
    )

    assert created.phase == "QUEUED"
    assert created.runtime == "Python"
    assert created.artifact_name == "solution.py"
    assert tx.commits == 1
    assert len(outbox.jobs) == 1
    assert outbox.jobs[0].attempt_key == str(created.key)
    assert str(created.key) in attempts.items


def test_empty_source_is_rejected_before_persistence() -> None:
    svc, tx, _attempts, outbox = service()
    with pytest.raises(ValidationError, match="sourceText is empty"):
        run(svc.create(OpenAttemptCommand("demo-1", "Python", "   "), x_handle=None, x_account_key=None))
    assert tx.commits == 0
    assert outbox.jobs == []


def test_unknown_challenge_is_reported_as_not_found() -> None:
    svc, *_ = service(available_challenge=None)
    svc._challenges.challenge = None
    with pytest.raises(NotFoundError):
        run(svc.create(OpenAttemptCommand("missing", "Python", "print(1)"), x_handle=None, x_account_key=None))


def test_language_policy_is_case_insensitive_but_returns_canonical_label() -> None:
    svc, *_ = service()
    created = run(svc.create(OpenAttemptCommand("demo-1", "c++", "int main(){}"), x_handle=None, x_account_key=None))
    assert created.runtime == "C++"


def test_disallowed_language_does_not_queue_work() -> None:
    svc, tx, _attempts, outbox = service()
    with pytest.raises(ValidationError, match="not enabled"):
        run(svc.create(OpenAttemptCommand("demo-1", "Rust", "fn main(){}"), x_handle=None, x_account_key=None))
    assert tx.commits == 0
    assert outbox.jobs == []


def test_request_key_returns_existing_attempt() -> None:
    svc, tx, attempts, outbox = service()
    first = run(
        svc.create(
            OpenAttemptCommand("demo-1", "Python", "print(1)"),
            x_handle=None,
            x_account_key=None,
            request_key="same-request",
        )
    )
    second = run(
        svc.create(
            OpenAttemptCommand("demo-1", "Python", "print(999)"),
            x_handle=None,
            x_account_key=None,
            request_key="same-request",
        )
    )
    assert second.key == first.key
    assert len(attempts.items) == 1
    assert len(outbox.jobs) == 1
    assert tx.commits == 1


def test_invalid_actor_filter_is_mapped_to_validation_error() -> None:
    svc, *_ = service()

    async def invalid_page(**query):
        raise ValueError("invalid account key")

    svc._attempts.page = invalid_page
    with pytest.raises(ValidationError, match="invalid account key"):
        run(svc.list(AttemptQuery(actor_key="not-a-uuid")))
