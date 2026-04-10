from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.models import AccessGrant
from app.application.vk_events import build_vk_event_application_handler
from app.db.base import Base
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

    def test_vk_flow_returns_deny_when_user_has_no_grant(self) -> None:
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

            decision = handler.handle(event)
            users = session.execute(select(User)).scalars().all()

        self.assertIsNotNone(decision)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "grant_missing")
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].vk_user_id, 123456)

    def test_vk_flow_returns_allow_when_user_has_grant(self) -> None:
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

            decision = handler.handle(event)

        self.assertIsNotNone(decision)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "grant_present")

    def test_vk_flow_noops_when_actor_id_is_missing(self) -> None:
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

            decision = handler.handle(event)
            users = session.execute(select(User)).scalars().all()

        self.assertIsNone(decision)
        self.assertEqual(users, [])
