from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AccountState(StrEnum):
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class AccountInactiveError(Exception):
    pass


@dataclass
class TenantAccount:
    tenant_id: str
    state: AccountState = AccountState.ONBOARDING

    def activate(self) -> None:
        if self.state not in {AccountState.ONBOARDING, AccountState.SUSPENDED}:
            raise ValueError(f"cannot activate account from {self.state}")
        self.state = AccountState.ACTIVE

    def suspend(self) -> None:
        if self.state is not AccountState.ACTIVE:
            raise ValueError(f"cannot suspend account from {self.state}")
        self.state = AccountState.SUSPENDED

    def close(self) -> None:
        self.state = AccountState.CLOSED

    def require_image_processing(self) -> None:
        if self.state is not AccountState.ACTIVE:
            raise AccountInactiveError(f"tenant {self.tenant_id} is {self.state}")
