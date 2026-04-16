from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.vk_events import build_vk_event_application_handler
from app.db.base import Base
from app.users.models import User
from app.users.service import UserService
from app.vk_transport.schemas import NormalizedVkEvent


class ProviderSelectionTests(unittest.TestCase):
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

    def test_button_text_selects_provider_and_returns_handled_outcome(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-1",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={"message": {"text": "⚡ Gemini"}},
        )

        with self.session_factory() as session:
            handler = build_vk_event_application_handler(session)
            outcome = handler.handle(event)
            user = session.execute(select(User)).scalar_one()

        self.assertEqual(outcome.status, "handled")
        self.assertEqual(outcome.reason, "provider_selected")
        self.assertEqual(user.selected_provider, "gemini")
        self.assertIn("Gemini", event.payload["handled_text"])

    def test_provider_button_payload_selects_provider(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-1-payload",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={
                "message": {
                    "text": "⚡ Gemini",
                    "payload": '{"type":"provider_select","provider":"gemini"}',
                }
            },
        )

        with self.session_factory() as session:
            handler = build_vk_event_application_handler(session)
            outcome = handler.handle(event)
            user = session.execute(select(User)).scalar_one()

        self.assertEqual(outcome.status, "handled")
        self.assertEqual(outcome.reason, "provider_selected")
        self.assertEqual(user.selected_provider, "gemini")
        self.assertIn("Gemini", event.payload["handled_text"])

    def test_normal_text_keeps_selected_provider_unchanged(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-2",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000001,
            payload={"message": {"text": "hello"}},
        )

        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            UserService(session).set_selected_provider(user_id=user.id, provider_code="claude")
            handler = build_vk_event_application_handler(session)
            outcome = handler.handle(event)
            stored = session.execute(select(User)).scalar_one()

        self.assertNotEqual(outcome.status, "handled")
        self.assertEqual(stored.selected_provider, "claude")
