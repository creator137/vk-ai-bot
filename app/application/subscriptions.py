from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.subscriptions.service import SubscriptionService
from app.users.service import UserService


@dataclass(frozen=True, slots=True)
class SubscriptionIssueResult:
    vk_user_id: int
    user_id: int
    plan_code: str
    included_tokens: int
    used_tokens: int


class SubscriptionIssuanceHandler:
    def __init__(
        self,
        user_service: UserService,
        subscription_service: SubscriptionService,
    ) -> None:
        self._user_service = user_service
        self._subscription_service = subscription_service

    def issue_for_vk_user_id(
        self,
        *,
        vk_user_id: int,
        plan_code: str,
    ) -> SubscriptionIssueResult:
        user = self._user_service.find_or_create_by_vk_user_id(vk_user_id)
        issued = self._subscription_service.issue_for_user_id(
            user_id=user.id,
            plan_code=plan_code,
        )
        return SubscriptionIssueResult(
            vk_user_id=user.vk_user_id,
            user_id=user.id,
            plan_code=issued.plan_code,
            included_tokens=issued.included_tokens,
            used_tokens=issued.used_tokens,
        )


def build_subscription_issuance_handler(session: Session) -> SubscriptionIssuanceHandler:
    return SubscriptionIssuanceHandler(
        user_service=UserService(session=session),
        subscription_service=SubscriptionService(session=session),
    )
