from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.models import AccessGrant
from app.access.service import AccessService
from app.db.base import Base
from app.subscriptions.service import SubscriptionService
from app.users.service import UserService


class AccessServiceTests(unittest.TestCase):
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

    def test_access_denied_when_no_grant_or_subscription_exists(self) -> None:
        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            service = AccessService(session=session)

            decision = service.decide_for_user_id(user.id)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "subscription_missing")

    def test_access_allowed_when_grant_exists(self) -> None:
        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            session.add(AccessGrant(user_id=user.id))
            session.commit()
            service = AccessService(session=session)

            decision = service.decide_for_user_id(user.id)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "grant_present")

    def test_access_allowed_when_active_subscription_exists(self) -> None:
        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            SubscriptionService(session=session).issue_for_user_id(
                user_id=user.id,
                plan_code="lite",
            )
            service = AccessService(session=session)

            decision = service.decide_for_user_id(user.id)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "subscription_active")

    def test_access_grant_enforces_single_grant_per_user(self) -> None:
        with self.session_factory() as session:
            user_id = UserService(session).find_or_create_by_vk_user_id(123456).id
            session.add(AccessGrant(user_id=user_id))
            session.commit()

        with self.session_factory() as session:
            session.add(AccessGrant(user_id=user_id))

            with self.assertRaises(IntegrityError):
                session.commit()

    def test_access_grant_issuance_is_idempotent(self) -> None:
        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            service = AccessService(session=session)

            first_issuance = service.issue_for_user_id(user.id)
            second_issuance = service.issue_for_user_id(user.id)

        self.assertTrue(first_issuance.created)
        self.assertFalse(second_issuance.created)
