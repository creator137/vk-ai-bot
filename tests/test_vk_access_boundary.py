from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.models import AccessGrant
from app.application.vk_events import build_vk_event_application_handler
from app.core.config import Settings
from app.db.base import Base
from app.subscriptions.service import SubscriptionService
from app.users.models import User
from app.users.service import UserService
from app.vk_transport.schemas import NormalizedVkEvent


class VkAccessBoundaryTests(unittest.TestCase):
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

    def test_vk_flow_returns_accepted_for_new_user_with_starter_tokens(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-1",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={"message": {"text": "hello"}},
        )

        with self.session_factory() as session:
            handler = build_vk_event_application_handler(session)

            outcome = handler.handle(event)
            users = session.execute(select(User)).scalars().all()

        self.assertEqual(outcome.status, "accepted")
        self.assertEqual(outcome.reason, "access_allowed")
        self.assertEqual(outcome.user_id, users[0].id)
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].vk_user_id, 123456)

    def test_vk_flow_returns_accepted_when_user_has_grant(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-1",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={"message": {"text": "hello"}},
        )

        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            session.add(AccessGrant(user_id=user.id))
            session.commit()
            handler = build_vk_event_application_handler(session)

            outcome = handler.handle(event)

        self.assertEqual(outcome.status, "accepted")
        self.assertEqual(outcome.reason, "access_allowed")
        self.assertEqual(outcome.user_id, user.id)

    def test_vk_flow_returns_accepted_when_user_has_active_subscription(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-1",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={"message": {"text": "hello"}},
        )

        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            SubscriptionService(session=session).issue_for_user_id(
                user_id=user.id,
                plan_code="lite",
            )
            handler = build_vk_event_application_handler(session)

            outcome = handler.handle(event)

        self.assertEqual(outcome.status, "accepted")
        self.assertEqual(outcome.reason, "access_allowed")
        self.assertEqual(outcome.user_id, user.id)

    def test_vk_flow_notifies_user_when_daily_free_bonus_is_issued(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-daily-bonus",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={"message": {"text": "hello"}},
        )

        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            subscription_service = SubscriptionService(session=session)
            subscription_service.consume_tokens_if_present(user_id=user.id, total_tokens=5_000)

            with patch(
                "app.application.vk_events.get_settings",
                return_value=Settings(
                    ai_provider="claude",
                    vk_outbound_token="test-token",
                    vk_api_version="5.199",
                ),
            ):
                with patch("app.application.vk_events.VkMessagesApi.send_text_message") as send_text_message:
                    handler = build_vk_event_application_handler(session)
                    outcome = handler.handle(event)

        self.assertEqual(outcome.status, "accepted")
        self.assertEqual(outcome.reason, "access_allowed")
        send_text_message.assert_called_once()
        self.assertEqual(send_text_message.call_args.kwargs["peer_id"], 123456)
        self.assertIn(
            "ежедневные 3 000 токенов",
            send_text_message.call_args.kwargs["text"],
        )

    def test_vk_flow_returns_skipped_when_actor_id_is_missing(self) -> None:
        event = NormalizedVkEvent(
            event_type="group_join",
            group_id=1,
            event_id="evt-2",
            actor_id=None,
            peer_id=None,
            occurred_at=1710000001,
            payload={},
        )

        with self.session_factory() as session:
            handler = build_vk_event_application_handler(session)

            outcome = handler.handle(event)
            users = session.execute(select(User)).scalars().all()

        self.assertEqual(outcome.status, "skipped")
        self.assertEqual(outcome.reason, "missing_actor_id")
        self.assertIsNone(outcome.user_id)
        self.assertEqual(users, [])
