from __future__ import annotations

from control_plane.runtime.use_cases.errors import NotFoundError
from control_plane.runtime.use_cases.ports import Transaction, AccountDirectory
from control_plane.runtime.core.entities import Account


class AccountService:
    def __init__(self, accounts: AccountDirectory, transaction: Transaction, *, default_handle: str) -> None:
        self._accounts = accounts
        self._transaction = transaction
        self._default_handle = default_handle

    async def current(self) -> Account:
        account = await self._accounts.get_or_create(self._default_handle)
        await self._transaction.commit()
        return account

    async def require_by_handle(self, handle: str) -> Account:
        account = await self._accounts.find_by_handle(handle)
        if account is None:
            raise NotFoundError("account not found")
        return account
