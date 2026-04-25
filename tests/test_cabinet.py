from __future__ import annotations

from datetime import date
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.service import AccessService
from app.core.config import Settings
from app.application.cabinet import CabinetService
from app.application.vk_events import build_vk_event_application_handler
from app.db.base import Base
from app.subscriptions.service import SubscriptionService
from app.users.service import UserService
from app.vk_transport.schemas import NormalizedVkEvent


class CabinetTests(unittest.TestCase):
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

    def test_cabinet_shows_plan_remaining_tokens_and_provider(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-cabinet",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={"message": {"text": "Личный кабинет"}},
        )

        with self.session_factory() as session:
            user_service = UserService(session)
            user = user_service.find_or_create_by_vk_user_id(123456)
            user_service.set_selected_provider(user_id=user.id, provider_code="claude")
            subscription_service = SubscriptionService(session=session)
            subscription_service.issue_for_user_id(user_id=user.id, plan_code="pro")
            subscription_service.consume_tokens_if_present(user_id=user.id, total_tokens=1234)

            handler = build_vk_event_application_handler(session)
            outcome = handler.handle(event)

        self.assertEqual(outcome.status, "handled")
        self.assertEqual(outcome.reason, "cabinet_shown")
        self.assertIn("🟩 Ваш ID: 123456", event.payload["handled_text"])
        self.assertIn("💎 Подписка: Pro", event.payload["handled_text"])
        self.assertIn("🔹 Баланс: 98 766 токенов", event.payload["handled_text"])
        self.assertIn("🤖 Активный ИИ: Claude", event.payload["handled_text"])
        self.assertIn("🚀 Что умеет ИИ:", event.payload["handled_text"])
        self.assertIn("📦 Лимит тарифа: 100 000 токенов", event.payload["handled_text"])

    def test_cabinet_shows_starter_bonus_for_new_user(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-cabinet-2",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={"message": {"text": "кабинет"}},
        )

        with self.session_factory() as session:
            user = UserService(session).find_or_create_by_vk_user_id(123456)
            AccessService(session=session).issue_for_user_id(user.id)
            handler = build_vk_event_application_handler(session)
            outcome = handler.handle(event)

        self.assertEqual(outcome.status, "handled")
        self.assertEqual(outcome.reason, "cabinet_shown")
        self.assertIn("🟩 Ваш ID: 123456", event.payload["handled_text"])
        self.assertIn("💎 Подписка: Free", event.payload["handled_text"])
        self.assertIn("🔹 Баланс: 5 000 токенов", event.payload["handled_text"])
        self.assertIn("📦 Лимит тарифа: 5 000 токенов", event.payload["handled_text"])

    def test_cabinet_shows_daily_free_balance_as_3000_after_exhaustion(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-cabinet-daily-free",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={"message": {"text": "кабинет"}},
        )

        with self.session_factory() as session:
            user_service = UserService(session)
            user = user_service.find_or_create_by_vk_user_id(123456)
            subscription_service = SubscriptionService(session=session)
            subscription_service.consume_tokens_if_present(user_id=user.id, total_tokens=5_000)
            subscription_service.issue_daily_exhausted_bonus_for_user_id(
                user_id=user.id,
                current_date=date(2026, 4, 23),
            )

            handler = build_vk_event_application_handler(session)
            outcome = handler.handle(event)

        self.assertEqual(outcome.status, "handled")
        self.assertEqual(outcome.reason, "cabinet_shown")
        self.assertIn("💎 Подписка: Free", event.payload["handled_text"])
        self.assertIn("🔹 Баланс: 3 000 токенов", event.payload["handled_text"])
        self.assertIn("📦 Лимит тарифа: 3 000 токенов", event.payload["handled_text"])

    def test_return_to_cabinet_phrase_opens_cabinet(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-cabinet-3",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={"message": {"text": "Вернуться в личный кабинет"}},
        )

        with self.session_factory() as session:
            UserService(session).find_or_create_by_vk_user_id(123456)
            handler = build_vk_event_application_handler(session)
            outcome = handler.handle(event)

        self.assertEqual(outcome.status, "handled")
        self.assertEqual(outcome.reason, "cabinet_shown")
        self.assertIn("🟥 Ваш ID: 123456", event.payload["handled_text"])

    def test_cabinet_button_payload_opens_cabinet(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-cabinet-payload",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={
                "message": {
                    "text": "🏠 Кабинет",
                    "payload": '{"type":"cabinet_open"}',
                }
            },
        )

        with self.session_factory() as session:
            UserService(session).find_or_create_by_vk_user_id(123456)
            handler = build_vk_event_application_handler(session)
            outcome = handler.handle(event)

        self.assertEqual(outcome.status, "handled")
        self.assertEqual(outcome.reason, "cabinet_shown")
        self.assertIn("🚀 Что умеет ИИ:", event.payload["handled_text"])

    def test_plans_phrase_opens_plans_text(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-cabinet-4",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={"message": {"text": "Тарифы"}},
        )

        with self.session_factory() as session:
            UserService(session).find_or_create_by_vk_user_id(123456)
            handler = build_vk_event_application_handler(session)
            outcome = handler.handle(event)

        self.assertEqual(outcome.status, "handled")
        self.assertEqual(outcome.reason, "plans_shown")
        self.assertIn("💎 Премиум — это:", event.payload["handled_text"])

    def test_plans_button_payload_opens_plans_text(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-cabinet-4-payload",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={
                "message": {
                    "text": "💎 Тарифы",
                    "payload": '{"type":"plans_open"}',
                }
            },
        )

        with self.session_factory() as session:
            UserService(session).find_or_create_by_vk_user_id(123456)
            handler = build_vk_event_application_handler(session)
            outcome = handler.handle(event)

        self.assertEqual(outcome.status, "handled")
        self.assertEqual(outcome.reason, "plans_shown")
        self.assertIn("Выбери свой уровень по лучшим ценам", event.payload["handled_text"])

    def test_plan_button_opens_plan_preview(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-cabinet-5",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={"message": {"text": "🚀 Pro"}},
        )

        with self.session_factory() as session:
            UserService(session).find_or_create_by_vk_user_id(123456)
            handler = build_vk_event_application_handler(session)
            outcome = handler.handle(event)

        self.assertEqual(outcome.status, "handled")
        self.assertEqual(outcome.reason, "plan_preview_shown")
        self.assertIn("⭐️ PRO — 599₽", event.payload["handled_text"])
        self.assertIn("🔥100.000 токенов🔥", event.payload["handled_text"])
        self.assertIn("Оплата появится", event.payload["handled_text"])

    def test_plan_button_payload_opens_plan_preview(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-cabinet-5-payload",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={
                "message": {
                    "text": "🚀 Pro",
                    "payload": '{"type":"plan_open","plan":"pro"}',
                }
            },
        )

        with self.session_factory() as session:
            UserService(session).find_or_create_by_vk_user_id(123456)
            handler = build_vk_event_application_handler(session)
            outcome = handler.handle(event)

        self.assertEqual(outcome.status, "handled")
        self.assertEqual(outcome.reason, "plan_preview_shown")
        self.assertIn("⭐️ PRO — 599₽", event.payload["handled_text"])

    def test_plan_preview_contains_payment_link_when_robokassa_is_configured(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-cabinet-6",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={"message": {"text": "🚀 Pro"}},
        )

        with patch(
            "app.application.vk_events.get_settings",
            return_value=Settings(
                app_base_url="https://vegagpt.ru",
                robokassa_merchant_login="demo",
                robokassa_password1="pass1",
                robokassa_password2="pass2",
                robokassa_test_mode=True,
            ),
        ):
            with self.session_factory() as session:
                UserService(session).find_or_create_by_vk_user_id(123456)
                handler = build_vk_event_application_handler(session)
                outcome = handler.handle(event)

        self.assertEqual(outcome.status, "handled")
        self.assertEqual(outcome.reason, "plan_preview_shown")
        self.assertIn("Нажмите кнопку оплаты ниже", event.payload["handled_text"])
        self.assertNotIn("auth.robokassa.ru", event.payload["handled_text"])
        self.assertEqual(event.payload["handled_view"], "plan_detail")
        self.assertIn("handled_payment_url", event.payload)
        self.assertTrue(event.payload["handled_image_path"].endswith("pro.jpeg"))

    def test_instruction_phrase_opens_instruction_text(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-cabinet-7",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={"message": {"text": "Инструкция"}},
        )

        with self.session_factory() as session:
            UserService(session).find_or_create_by_vk_user_id(123456)
            handler = build_vk_event_application_handler(session)
            outcome = handler.handle(event)

        self.assertEqual(outcome.status, "handled")
        self.assertEqual(outcome.reason, "instruction_shown")
        self.assertIn("📘 Инструкция", event.payload["handled_text"])
        self.assertIn("@zhigunov3", event.payload["handled_text"])

    def test_support_button_payload_opens_support_text(self) -> None:
        event = NormalizedVkEvent(
            event_type="message_new",
            group_id=1,
            event_id="evt-cabinet-8",
            actor_id=123456,
            peer_id=321,
            occurred_at=1710000000,
            payload={
                "message": {
                    "text": "🆘 Поддержка",
                    "payload": '{"type":"support_open"}',
                }
            },
        )

        with self.session_factory() as session:
            UserService(session).find_or_create_by_vk_user_id(123456)
            handler = build_vk_event_application_handler(session)
            outcome = handler.handle(event)

        self.assertEqual(outcome.status, "handled")
        self.assertEqual(outcome.reason, "support_shown")
        self.assertIn("🆘 Поддержка", event.payload["handled_text"])
        self.assertIn("@zhigunov3", event.payload["handled_text"])
