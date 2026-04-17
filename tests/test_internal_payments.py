from __future__ import annotations

import unittest
from collections.abc import Generator
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.payments.models import SubscriptionPayment


class InternalPaymentsEndpointTests(unittest.TestCase):
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
            app_base_url="https://vegagpt.ru",
            robokassa_merchant_login="demo",
            robokassa_password1="pass1",
            robokassa_password2="pass2",
            robokassa_test_mode=True,
        )

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_create_robokassa_payment_returns_payment_url(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/internal/payments/robokassa",
                json={"vk_user_id": 123456, "plan_code": "pro"},
                headers={"X-Internal-Token": "internal-secret"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["vk_user_id"], 123456)
        self.assertEqual(body["plan_code"], "pro")
        self.assertEqual(body["amount_rub"], 599)
        self.assertTrue(body["is_test"])

        parsed = urlparse(body["payment_url"])
        params = parse_qs(parsed.query)
        self.assertEqual(params["MerchantLogin"], ["demo"])
        self.assertEqual(params["OutSum"], ["599.00"])
        self.assertEqual(params["Shp_plan"], ["pro"])
        self.assertEqual(params["ResultUrl"], ["https://vegagpt.ru/payments/robokassa/result"])

        with self.session_factory() as session:
            payments = session.execute(select(SubscriptionPayment)).scalars().all()

        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0].status, "pending")
        self.assertEqual(payments[0].plan_code, "pro")

    def _override_db_session(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session
