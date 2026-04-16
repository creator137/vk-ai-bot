from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.subscriptions.models import UserSubscription


class UserSubscriptionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_user_id(self, user_id: int) -> UserSubscription | None:
        statement = select(UserSubscription).where(UserSubscription.user_id == user_id)
        return self._session.execute(statement).scalar_one_or_none()

    def save(
        self,
        *,
        user_id: int,
        plan_code: str,
        included_tokens: int,
    ) -> UserSubscription:
        subscription = self.get_by_user_id(user_id)
        if subscription is None:
            subscription = UserSubscription(
                user_id=user_id,
                plan_code=plan_code,
                included_tokens=included_tokens,
                used_tokens=0,
            )
            self._session.add(subscription)
            self._session.flush()
            return subscription

        subscription.plan_code = plan_code
        subscription.included_tokens = included_tokens
        subscription.used_tokens = 0
        self._session.flush()
        return subscription
