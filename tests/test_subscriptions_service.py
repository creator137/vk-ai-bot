from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.subscriptions.service import SubscriptionService
from app.users.service import UserService


class SubscriptionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )
        Base.metadata.create_all(self.engine)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_issue_creates_active_subscription(self) -> None:
        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            service = SubscriptionService(session=session)

            issued = service.issue_for_user_id(user_id=user.id, plan_code="lite")
            decision = service.decide_for_user_id(user.id)

        self.assertEqual(issued.plan_code, "lite")
        self.assertEqual(issued.included_tokens, 35_000)
        self.assertEqual(issued.used_tokens, 0)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "subscription_active")

    def test_decision_becomes_denied_after_tokens_are_exhausted(self) -> None:
        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            service = SubscriptionService(session=session)
            service.issue_for_user_id(user_id=user.id, plan_code="lite")

            service.consume_tokens_if_present(user_id=user.id, total_tokens=35_000)
            decision = service.decide_for_user_id(user.id)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "subscription_exhausted")
