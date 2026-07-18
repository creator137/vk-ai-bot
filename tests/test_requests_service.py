from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.requests.models import AcceptedRequestRecord
from app.requests.service import AcceptedRequestPersistenceService
from app.users.models import User


class AcceptedRequestPersistenceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_records_accepted_text_exchange(self) -> None:
        with Session(self.engine) as session:
            user = User(vk_user_id=123456)
            session.add(user)
            session.commit()
            session.refresh(user)
            user_id = user.id

            service = AcceptedRequestPersistenceService(session=session)
            recorded = service.record_text_exchange(
                user_id=user_id,
                peer_id=321,
                request_text="hello",
                response_text="AI reply",
                input_tokens=10,
                output_tokens=6,
                total_tokens=16,
            )

            stored = session.scalar(select(AcceptedRequestRecord))

        self.assertIsNotNone(stored)
        self.assertEqual(recorded.user_id, user_id)
        self.assertEqual(recorded.peer_id, 321)
        self.assertEqual(recorded.request_text, "hello")
        self.assertEqual(recorded.response_text, "AI reply")
        self.assertEqual(recorded.input_tokens, 10)
        self.assertEqual(recorded.output_tokens, 6)
        self.assertEqual(recorded.total_tokens, 16)
        self.assertEqual(stored.user_id, user_id)
        self.assertEqual(stored.peer_id, 321)
        self.assertEqual(stored.request_text, "hello")
        self.assertEqual(stored.response_text, "AI reply")
        self.assertEqual(stored.input_tokens, 10)
        self.assertEqual(stored.output_tokens, 6)
        self.assertEqual(stored.total_tokens, 16)

    def test_lists_recent_dialogue_turns_in_chronological_order(self) -> None:
        with Session(self.engine) as session:
            user = User(vk_user_id=123456)
            session.add(user)
            session.commit()
            session.refresh(user)

            service = AcceptedRequestPersistenceService(session=session)
            service.record_text_exchange(
                user_id=user.id,
                peer_id=321,
                request_text="first",
                response_text="first reply",
                input_tokens=1,
                output_tokens=1,
                total_tokens=2,
            )
            service.record_text_exchange(
                user_id=user.id,
                peer_id=321,
                request_text="second",
                response_text="second reply",
                input_tokens=1,
                output_tokens=1,
                total_tokens=2,
            )
            service.record_text_exchange(
                user_id=user.id,
                peer_id=321,
                request_text="third",
                response_text="third reply",
                input_tokens=1,
                output_tokens=1,
                total_tokens=2,
            )

            turns = service.list_recent_dialogue_turns(
                user_id=user.id,
                peer_id=321,
                limit=2,
            )

        self.assertEqual(
            [(turn.request_text, turn.response_text) for turn in turns],
            [("second", "second reply"), ("third", "third reply")],
        )
