from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.payments.models import SubscriptionPayment


class SubscriptionPaymentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        user_id: int,
        plan_code: str,
        amount_rub: int,
    ) -> SubscriptionPayment:
        payment = SubscriptionPayment(
            user_id=user_id,
            plan_code=plan_code,
            amount_rub=amount_rub,
            status="pending",
        )
        self._session.add(payment)
        self._session.flush()
        return payment

    def get_by_id(self, payment_id: int) -> SubscriptionPayment | None:
        statement = select(SubscriptionPayment).where(SubscriptionPayment.id == payment_id)
        return self._session.execute(statement).scalar_one_or_none()
