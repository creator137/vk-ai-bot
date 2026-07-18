from __future__ import annotations

import unittest
from collections.abc import Generator
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.payments.models import SubscriptionPayment
from app.payments.robokassa import RobokassaSignatureBuilder
from app.subscriptions.models import UserSubscription
from app.users.models import User


class RobokassaRoutesTests(unittest.TestCase):
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

    def test_result_callback_marks_payment_paid_and_issues_subscription(self) -> None:
        with self.session_factory() as session:
            user = User(vk_user_id=123456)
            session.add(user)
            session.commit()
            session.refresh(user)

            payment = SubscriptionPayment(
                user_id=user.id,
                plan_code="pro",
                amount_rub=599,
                status="pending",
            )
            session.add(payment)
            session.commit()
            session.refresh(payment)
            payment_id = payment.id

        builder = RobokassaSignatureBuilder(
            merchant_login="demo",
            password1="pass1",
            password2="pass2",
        )
        signature = builder._sign_for_result(  # noqa: SLF001
            out_sum="599.00",
            invoice_id=payment_id,
            shp_params={"Shp_plan": "pro", "Shp_user": "1"},
        )

        with patch("app.application.payments.VkMessagesApi.send_text_message") as send_text_message:
            with TestClient(app) as client:
                response = client.post(
                    "/payments/robokassa/result",
                    data={
                        "OutSum": "599.00",
                        "InvId": str(payment_id),
                        "SignatureValue": signature,
                        "Shp_plan": "pro",
                        "Shp_user": "1",
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, f"OK{payment_id}")
        send_text_message.assert_called_once()
        self.assertEqual(send_text_message.call_args.kwargs["peer_id"], 123456)
        self.assertIn("Оплата прошла успешно.", send_text_message.call_args.kwargs["text"])
        self.assertIn("Тариф Pro активирован.", send_text_message.call_args.kwargs["text"])

        with self.session_factory() as session:
            payment = session.execute(select(SubscriptionPayment)).scalar_one()
            subscription = session.execute(select(UserSubscription)).scalar_one()

        self.assertEqual(payment.status, "paid")
        self.assertEqual(subscription.user_id, 1)
        self.assertEqual(subscription.plan_code, "pro")
        self.assertEqual(subscription.included_tokens, 100000)

    def test_success_redirect_accepts_valid_signature(self) -> None:
        with self.session_factory() as session:
            user = User(vk_user_id=123456)
            session.add(user)
            session.commit()
            session.refresh(user)

            payment = SubscriptionPayment(
                user_id=user.id,
                plan_code="lite",
                amount_rub=379,
                status="pending",
            )
            session.add(payment)
            session.commit()
            session.refresh(payment)
            payment_id = payment.id

        builder = RobokassaSignatureBuilder(
            merchant_login="demo",
            password1="pass1",
            password2="pass2",
        )
        signature = builder._sign_for_success(  # noqa: SLF001
            out_sum="379.00",
            invoice_id=payment_id,
            shp_params={"Shp_plan": "lite", "Shp_user": "1"},
        )

        with patch("app.application.payments.VkMessagesApi.send_text_message") as send_text_message:
            with TestClient(app) as client:
                response = client.get(
                    "/payments/robokassa/success",
                    params={
                        "OutSum": "379.00",
                        "InvId": str(payment_id),
                        "SignatureValue": signature,
                        "Shp_plan": "lite",
                        "Shp_user": "1",
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Подписка", response.text)
        send_text_message.assert_called_once()
        self.assertEqual(send_text_message.call_args.kwargs["peer_id"], 123456)
        self.assertIn("Тариф Lite активирован.", send_text_message.call_args.kwargs["text"])

        with self.session_factory() as session:
            payment = session.execute(select(SubscriptionPayment)).scalar_one()
            subscription = session.execute(select(UserSubscription)).scalar_one()

        self.assertEqual(payment.status, "paid")
        self.assertEqual(subscription.plan_code, "lite")

    def test_result_callback_accepts_fallback_password_in_test_mode(self) -> None:
        app.dependency_overrides[get_settings] = lambda: Settings(
            app_base_url="https://vegagpt.ru",
            robokassa_merchant_login="demo",
            robokassa_password1="prod-pass1",
            robokassa_password2="prod-pass2",
            robokassa_password1_test="test-pass1",
            robokassa_password2_test="test-pass2",
            robokassa_test_mode=True,
        )

        with self.session_factory() as session:
            user = User(vk_user_id=123456)
            session.add(user)
            session.commit()
            session.refresh(user)

            payment = SubscriptionPayment(
                user_id=user.id,
                plan_code="lite",
                amount_rub=379,
                status="pending",
            )
            session.add(payment)
            session.commit()
            session.refresh(payment)
            payment_id = payment.id

        builder = RobokassaSignatureBuilder(
            merchant_login="demo",
            password1="prod-pass1",
            password2="prod-pass2",
            hash_algorithm="md5",
            test_mode=True,
        )
        signature = builder._sign_for_result(  # noqa: SLF001
            out_sum="379.00",
            invoice_id=payment_id,
            shp_params={"Shp_plan": "lite", "Shp_user": "1"},
        )

        with TestClient(app) as client:
            response = client.post(
                "/payments/robokassa/result",
                data={
                    "OutSum": "379.00",
                    "InvId": str(payment_id),
                    "SignatureValue": signature,
                    "Shp_plan": "lite",
                    "Shp_user": "1",
                    "IsTest": "1",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, f"OK{payment_id}")

        with self.session_factory() as session:
            payment = session.execute(select(SubscriptionPayment)).scalar_one()
            subscription = session.execute(select(UserSubscription)).scalar_one()

        self.assertEqual(payment.status, "paid")
        self.assertEqual(subscription.plan_code, "lite")

    def test_result_callback_logs_rejection_reason_for_invalid_signature(self) -> None:
        with self.session_factory() as session:
            user = User(vk_user_id=123456)
            session.add(user)
            session.commit()
            session.refresh(user)

            payment = SubscriptionPayment(
                user_id=user.id,
                plan_code="pro",
                amount_rub=599,
                status="pending",
            )
            session.add(payment)
            session.commit()
            session.refresh(payment)
            payment_id = payment.id

        with self.assertLogs("app.api.routes.robokassa", level="WARNING") as captured:
            with TestClient(app) as client:
                response = client.post(
                    "/payments/robokassa/result",
                    data={
                        "OutSum": "599.00",
                        "InvId": str(payment_id),
                        "SignatureValue": "bad-signature",
                        "Shp_plan": "pro",
                        "Shp_user": "1",
                    },
                )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid Robokassa result signature")
        self.assertTrue(
            any(
                "Robokassa result callback rejected" in message
                and "invoice_id=1" in message
                and "error=Invalid Robokassa result signature" in message
                for message in captured.output
            )
        )

    def _override_db_session(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session
