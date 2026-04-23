from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Literal

from sqlalchemy.orm import Session

from app.subscriptions.catalog import get_subscription_plan
from app.subscriptions.models import UserSubscription
from app.subscriptions.repository import UserSubscriptionRepository


@dataclass(frozen=True, slots=True)
class SubscriptionAccessDecision:
    allowed: bool
    reason: Literal["subscription_active", "subscription_missing", "subscription_exhausted"]


@dataclass(frozen=True, slots=True)
class SubscriptionIssue:
    user_id: int
    plan_code: str
    included_tokens: int
    used_tokens: int


class SubscriptionService:
    DAILY_EXHAUSTED_BONUS_TOKENS = 3_000

    def __init__(
        self,
        session: Session,
        repository: UserSubscriptionRepository | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or UserSubscriptionRepository(session)

    def decide_for_user_id(self, user_id: int) -> SubscriptionAccessDecision:
        subscription = self._repository.get_by_user_id(user_id)
        if subscription is None:
            return SubscriptionAccessDecision(False, "subscription_missing")

        self._grant_daily_tokens_if_eligible(subscription)
        if subscription.included_tokens - subscription.used_tokens <= 0:
            return SubscriptionAccessDecision(False, "subscription_exhausted")

        return SubscriptionAccessDecision(True, "subscription_active")

    def issue_for_user_id(self, *, user_id: int, plan_code: str) -> SubscriptionIssue:
        plan = get_subscription_plan(plan_code)
        subscription = self._repository.save(
            user_id=user_id,
            plan_code=plan.code,
            included_tokens=plan.included_tokens,
        )
        self._session.commit()
        self._session.refresh(subscription)
        return _build_issue(subscription)

    def issue_starter_for_user_id(self, *, user_id: int) -> SubscriptionIssue | None:
        if self._repository.get_by_user_id(user_id) is not None:
            return None

        plan = get_subscription_plan("free")
        subscription = self._repository.save(
            user_id=user_id,
            plan_code=plan.code,
            included_tokens=plan.included_tokens,
        )
        self._session.commit()
        self._session.refresh(subscription)
        return _build_issue(subscription)

    def issue_daily_exhausted_bonus_for_user_id(
        self,
        *,
        user_id: int,
        current_date: date | None = None,
    ) -> SubscriptionIssue | None:
        subscription = self._repository.get_by_user_id(user_id)
        if subscription is None:
            return None

        if not self._grant_daily_tokens_if_eligible(subscription, current_date=current_date):
            return None

        self._session.refresh(subscription)
        return _build_issue(subscription)

    def consume_tokens_if_present(self, *, user_id: int, total_tokens: int) -> None:
        if total_tokens <= 0:
            return

        subscription = self._repository.get_by_user_id(user_id)
        if subscription is None:
            return

        subscription.used_tokens += total_tokens
        self._session.commit()

    def get_subscription(self, *, user_id: int) -> UserSubscription | None:
        subscription = self._repository.get_by_user_id(user_id)
        if subscription is None:
            return None

        self._grant_daily_tokens_if_eligible(subscription)
        return subscription

    def _grant_daily_tokens_if_eligible(
        self,
        subscription: UserSubscription,
        *,
        current_date: date | None = None,
    ) -> bool:
        remaining_tokens = subscription.included_tokens - subscription.used_tokens
        if remaining_tokens > 0:
            return False

        issue_date = current_date or datetime.now(timezone.utc).date()
        if subscription.daily_tokens_last_issued_at == issue_date:
            return False

        subscription.included_tokens += self.DAILY_EXHAUSTED_BONUS_TOKENS
        subscription.daily_tokens_last_issued_at = issue_date
        self._session.commit()
        return True


def _build_issue(subscription: UserSubscription) -> SubscriptionIssue:
    return SubscriptionIssue(
        user_id=subscription.user_id,
        plan_code=subscription.plan_code,
        included_tokens=subscription.included_tokens,
        used_tokens=subscription.used_tokens,
    )
