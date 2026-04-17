from __future__ import annotations

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
        self.assertIn("AI BOT", event.payload["handled_text"])
        self.assertIn("✨ Личный кабинет", event.payload["handled_text"])
        self.assertIn("Умный помощник для идей, ответов и работы", event.payload["handled_text"])
        self.assertIn("• Активная модель: Claude", event.payload["handled_text"])
        self.assertIn("• Тариф: Pro", event.payload["handled_text"])
        self.assertIn("• Осталось: 98 766 из 100 000", event.payload["handled_text"])
        self.assertIn("Что можно сделать", event.payload["handled_text"])

    def test_cabinet_shows_no_plan_when_subscription_missing(self) -> None:
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
        self.assertIn("• Доступ: Активен", event.payload["handled_text"])
        self.assertIn("• Тариф: Free", event.payload["handled_text"])
        self.assertIn("Лимит пока не подключён", event.payload["handled_text"])

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
        self.assertIn("AI BOT", event.payload["handled_text"])

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
        self.assertIn("✨ Личный кабинет", event.payload["handled_text"])

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
        self.assertIn("💎 Тарифы", event.payload["handled_text"])

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
        self.assertIn("💎 Тарифы", event.payload["handled_text"])

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
        self.assertIn("🚀 Pro", event.payload["handled_text"])
        self.assertIn("599₽ в месяц", event.payload["handled_text"])
        self.assertIn("Оплата будет доступна", event.payload["handled_text"])

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
        self.assertIn("🚀 Pro", event.payload["handled_text"])

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
        self.assertIn("Ссылка на оплату:", event.payload["handled_text"])
        self.assertIn("auth.robokassa.ru", event.payload["handled_text"])
