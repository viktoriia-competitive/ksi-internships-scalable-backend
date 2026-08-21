from __future__ import annotations

import asyncio
import uuid

import pytest

from control_plane.runtime.use_cases.commands import ChallengeQuery
from control_plane.runtime.use_cases.errors import NotFoundError
from control_plane.runtime.use_cases.challenges import ChallengeService
from control_plane.runtime.use_cases.accounts import AccountService
from control_plane.runtime.core.entities import Account, Challenge, PageSlice


def run(coro):
    return asyncio.run(coro)


class Catalog:
    def __init__(self, item: Challenge | None) -> None:
        self.item = item
        self.last_query = None

    async def get(self, challenge_key: str):
        return self.item if self.item and self.item.key == challenge_key else None

    async def page(self, **query):
        self.last_query = query
        return PageSlice([self.item] if self.item else [], 1 if self.item else 0, query["index"], query["size"], 1)

    async def increment_accepted(self, challenge_key: str):
        return None


class Accounts:
    def __init__(self, item: Account | None) -> None:
        self.item = item

    async def get_or_create(self, handle: str):
        return self.item or Account(uuid.uuid4(), handle, 0, [])

    async def find_by_handle(self, handle: str):
        return self.item if self.item and self.item.handle == handle else None


class Tx:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        pass


def demo_challenge() -> Challenge:
    return Challenge("p1", "P1", "One", "easy", None, 0, "stdio", [], ["Python"], {"cpuMillis": 1000, "memoryMiB": 64}, {})


def test_challenge_query_is_passed_as_explicit_application_command() -> None:
    catalog = Catalog(demo_challenge())
    service = ChallengeService(catalog)
    page = run(service.list(ChallengeQuery(search="one", order_by="name", direction="desc", index=2, size=20)))
    assert page.entries[0].key == "p1"
    assert catalog.last_query["search"] == "one"
    assert catalog.last_query["order_by"] == "name"
    assert catalog.last_query["size"] == 20


def test_require_challenge_uses_domain_not_found_error() -> None:
    with pytest.raises(NotFoundError):
        run(ChallengeService(Catalog(None)).require("missing"))


def test_current_account_commits_creation_boundary() -> None:
    tx = Tx()
    service = AccountService(Accounts(None), tx, default_handle="local")
    current = run(service.current())
    assert current.handle == "local"
    assert tx.commits == 1


def test_lookup_missing_account_is_not_found() -> None:
    with pytest.raises(NotFoundError):
        run(AccountService(Accounts(None), Tx(), default_handle="local").require_by_handle("nobody"))
