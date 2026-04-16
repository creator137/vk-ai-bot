from __future__ import annotations

import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.subscriptions.models import UserSubscription
from app.users.models import User


class InternalSubscriptionEndpointTests(unittest.TestCase):
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
        app.dependency_overrides[get_db_session] = self._override_db_session
        app.dependency_overrides[get_settings] = lambda: Settings(
            internal_access_token="internal-secret",
        )

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_issuance_creates_subscription_for_vk_user_id(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/internal/subscriptions",
                json={"vk_user_id": 123456, "plan_code": "pro"},
                headers={"X-Internal-Token": "internal-secret"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "vk_user_id": 123456,
                "user_id": 1,
                "plan_code": "pro",
                "included_tokens": 100000,
                "used_tokens": 0,
            },
        )

        with self.session_factory() as session:
            users = session.execute(select(User)).scalars().all()
            subscriptions = session.execute(select(UserSubscription)).scalars().all()

        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].vk_user_id, 123456)
        self.assertEqual(len(subscriptions), 1)
        self.assertEqual(subscriptions[0].user_id, users[0].id)
        self.assertEqual(subscriptions[0].plan_code, "pro")
        self.assertEqual(subscriptions[0].included_tokens, 100000)

    def test_unauthorized_request_is_rejected(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/internal/subscriptions",
                json={"vk_user_id": 123456, "plan_code": "lite"},
                headers={"X-Internal-Token": "wrong-secret"},
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Invalid internal access token")

    def _override_db_session(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session
