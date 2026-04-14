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
            )

            stored = session.scalar(select(AcceptedRequestRecord))

        self.assertIsNotNone(stored)
        self.assertEqual(recorded.user_id, user_id)
        self.assertEqual(recorded.peer_id, 321)
        self.assertEqual(recorded.request_text, "hello")
        self.assertEqual(recorded.response_text, "AI reply")
        self.assertEqual(stored.user_id, user_id)
        self.assertEqual(stored.peer_id, 321)
        self.assertEqual(stored.request_text, "hello")
        self.assertEqual(stored.response_text, "AI reply")
