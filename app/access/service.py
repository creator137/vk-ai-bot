from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.access.repository import AccessGrantRepository
from app.subscriptions.service import SubscriptionService


@dataclass(frozen=True, slots=True)
class AccessDecision:
    allowed: bool
    reason: Literal[
        "grant_present",
        "subscription_active",
        "subscription_missing",
        "subscription_exhausted",
    ]


@dataclass(frozen=True, slots=True)
class AccessGrantIssuance:
    created: bool


class AccessService:
    def __init__(
        self,
        session: Session | None = None,
        repository: AccessGrantRepository | None = None,
        subscription_service: SubscriptionService | None = None,
    ) -> None:
        if session is None and repository is None:
            raise ValueError("AccessService requires a session or repository")

        self._repository = repository or AccessGrantRepository(session)
        self._session = session or self._repository._session
        self._subscription_service = subscription_service or SubscriptionService(self._session)

    def decide_for_user_id(self, user_id: int) -> AccessDecision:
        if self._repository.has_grant_for_user_id(user_id):
            return AccessDecision(allowed=True, reason="grant_present")

        subscription_decision = self._subscription_service.decide_for_user_id(user_id)
        if subscription_decision.allowed:
            return AccessDecision(allowed=True, reason="subscription_active")

        return AccessDecision(allowed=False, reason=subscription_decision.reason)

    def issue_for_user_id(self, user_id: int) -> AccessGrantIssuance:
        if self._repository.has_grant_for_user_id(user_id):
            return AccessGrantIssuance(created=False)

        try:
            self._repository.create_for_user_id(user_id)
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            if not self._repository.has_grant_for_user_id(user_id):
                raise
            return AccessGrantIssuance(created=False)

        return AccessGrantIssuance(created=True)
