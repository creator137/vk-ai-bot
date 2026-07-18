from __future__ import annotations

import json
import unittest
from collections.abc import Generator
from urllib.parse import unquote, urlparse

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
            robokassa_receipt_sno="usn_income",
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
            checkout_response = client.get(f"/payments/robokassa/start/{body['payment_id']}")

        body = response.json()
        self.assertEqual(body["vk_user_id"], 123456)
        self.assertEqual(body["plan_code"], "pro")
        self.assertEqual(body["amount_rub"], 500)
        self.assertTrue(body["is_test"])

        parsed = urlparse(body["payment_url"])
        self.assertEqual(parsed.path, "/payments/robokassa/start/1")

        self.assertEqual(checkout_response.status_code, 200)
        receipt_marker = 'name="Receipt" value="'
        receipt_start = checkout_response.text.index(receipt_marker) + len(receipt_marker)
        receipt_end = checkout_response.text.index('"', receipt_start)
        receipt_value = checkout_response.text[receipt_start:receipt_end]
        self.assertEqual(
            json.loads(unquote(receipt_value)),
            {
                "sno": "usn_income",
                "items": [
                    {
                        "name": "Подписка Pro",
                        "quantity": 1,
                        "sum": 500,
                        "payment_method": "full_prepayment",
                        "payment_object": "service",
                        "tax": "none",
                    }
                ],
            },
        )
        self.assertIn('name="MerchantLogin" value="demo"', checkout_response.text)
        self.assertIn('name="OutSum" value="500.00"', checkout_response.text)
        self.assertIn('name="Shp_plan" value="pro"', checkout_response.text)
        self.assertIn(
            'name="ResultUrl" value="https://vegagpt.ru/payments/robokassa/result"',
            checkout_response.text,
        )

        with self.session_factory() as session:
            payments = session.execute(select(SubscriptionPayment)).scalars().all()

        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0].status, "pending")
        self.assertEqual(payments[0].plan_code, "pro")

    def _override_db_session(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session
