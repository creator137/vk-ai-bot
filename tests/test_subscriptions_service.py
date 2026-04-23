from __future__ import annotations

from datetime import date
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

    def test_new_user_receives_one_time_starter_tokens(self) -> None:
        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            subscription = SubscriptionService(session=session).get_subscription(user_id=user.id)

        assert subscription is not None
        self.assertEqual(subscription.plan_code, "free")
        self.assertEqual(subscription.included_tokens, 5_000)
        self.assertEqual(subscription.used_tokens, 0)

    def test_starter_bonus_is_not_reissued_for_existing_user(self) -> None:
        with self.session_factory() as session:
            user_service = UserService(session)
            first_user = user_service.find_or_create_by_vk_user_id(123456)
            SubscriptionService(session=session).consume_tokens_if_present(
                user_id=first_user.id,
                total_tokens=1234,
            )

            second_user = user_service.find_or_create_by_vk_user_id(123456)
            subscription = SubscriptionService(session=session).get_subscription(user_id=second_user.id)

        assert subscription is not None
        self.assertEqual(first_user.id, second_user.id)
        self.assertEqual(subscription.plan_code, "free")
        self.assertEqual(subscription.used_tokens, 1234)

    def test_daily_bonus_is_issued_after_tokens_are_exhausted(self) -> None:
        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            service = SubscriptionService(session=session)
            service.consume_tokens_if_present(user_id=user.id, total_tokens=5_000)

            issued = service.issue_daily_exhausted_bonus_for_user_id(
                user_id=user.id,
                current_date=date(2026, 4, 23),
            )
            subscription = service.get_subscription(user_id=user.id)

        assert issued is not None
        assert subscription is not None
        self.assertEqual(issued.included_tokens, 8_000)
        self.assertEqual(subscription.included_tokens, 8_000)
        self.assertEqual(subscription.used_tokens, 5_000)

    def test_daily_bonus_is_not_issued_when_tokens_remain(self) -> None:
        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            service = SubscriptionService(session=session)

            issued = service.issue_daily_exhausted_bonus_for_user_id(
                user_id=user.id,
                current_date=date(2026, 4, 23),
            )
            subscription = service.get_subscription(user_id=user.id)

        self.assertIsNone(issued)
        assert subscription is not None
        self.assertEqual(subscription.included_tokens, 5_000)
        self.assertEqual(subscription.used_tokens, 0)

    def test_daily_bonus_is_not_reissued_on_same_day(self) -> None:
        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            service = SubscriptionService(session=session)
            service.consume_tokens_if_present(user_id=user.id, total_tokens=5_000)

            first_issue = service.issue_daily_exhausted_bonus_for_user_id(
                user_id=user.id,
                current_date=date(2026, 4, 23),
            )
            service.consume_tokens_if_present(user_id=user.id, total_tokens=3_000)
            second_issue = service.issue_daily_exhausted_bonus_for_user_id(
                user_id=user.id,
                current_date=date(2026, 4, 23),
            )
            subscription = service.get_subscription(user_id=user.id)

        self.assertIsNotNone(first_issue)
        self.assertIsNone(second_issue)
        assert subscription is not None
        self.assertEqual(subscription.included_tokens, 8_000)
        self.assertEqual(subscription.used_tokens, 8_000)

    def test_daily_bonus_can_be_issued_again_on_next_day(self) -> None:
        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            service = SubscriptionService(session=session)
            service.consume_tokens_if_present(user_id=user.id, total_tokens=5_000)
            service.issue_daily_exhausted_bonus_for_user_id(
                user_id=user.id,
                current_date=date(2026, 4, 23),
            )
            service.consume_tokens_if_present(user_id=user.id, total_tokens=3_000)

            next_issue = service.issue_daily_exhausted_bonus_for_user_id(
                user_id=user.id,
                current_date=date(2026, 4, 24),
            )
            decision = service.decide_for_user_id(user.id)
            subscription = service.get_subscription(user_id=user.id)

        self.assertIsNotNone(next_issue)
        self.assertTrue(decision.allowed)
        assert subscription is not None
        self.assertEqual(subscription.included_tokens, 11_000)
        self.assertEqual(subscription.used_tokens, 8_000)

    def test_decision_becomes_denied_after_tokens_are_exhausted(self) -> None:
        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            service = SubscriptionService(session=session)
            service.issue_for_user_id(user_id=user.id, plan_code="lite")

            service.consume_tokens_if_present(user_id=user.id, total_tokens=35_000)
            decision = service.decide_for_user_id(user.id)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "subscription_active")
