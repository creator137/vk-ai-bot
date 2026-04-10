from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.access.repository import AccessGrantRepository


@dataclass(frozen=True, slots=True)
class AccessDecision:
    allowed: bool
    reason: Literal["grant_present", "grant_missing"]


class AccessService:
    def __init__(self, repository: AccessGrantRepository) -> None:
        self._repository = repository

    def decide_for_user_id(self, user_id: int) -> AccessDecision:
        if self._repository.has_grant_for_user_id(user_id):
            return AccessDecision(allowed=True, reason="grant_present")

        return AccessDecision(allowed=False, reason="grant_missing")
