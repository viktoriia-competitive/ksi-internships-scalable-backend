"""Small account projection used by the local development identity."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from control_plane.runtime.contracts.attempts import AccountView
from control_plane.runtime.http.dependencies import account_service
from control_plane.runtime.http.presenters import account_view
from control_plane.runtime.use_cases.accounts import AccountService

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/self", response_model=AccountView)
async def self_account(service: Annotated[AccountService, Depends(account_service)]) -> AccountView:
    return account_view(await service.current())


@router.get("/by-handle/{handle}", response_model=AccountView)
async def account_by_handle(
    handle: str,
    service: Annotated[AccountService, Depends(account_service)],
) -> AccountView:
    return account_view(await service.require_by_handle(handle))
