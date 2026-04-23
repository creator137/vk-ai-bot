from __future__ import annotations

from dataclasses import dataclass
import re

from app.access.repository import AccessGrantRepository
from app.ai.provider_catalog import get_provider_option
from app.subscriptions.catalog import (
    find_subscription_plan_by_button_text,
    get_subscription_plan,
    get_subscription_plan_image_path,
    render_subscription_plan_detail_text,
    render_subscription_plans_text,
)
from app.subscriptions.service import SubscriptionService
from app.users.service import UserService


@dataclass(frozen=True, slots=True)
class CabinetSnapshot:
    user_id: int
    vk_user_id: int
    access_active: bool
    provider_title: str
    plan_title: str | None
    included_tokens: int | None
    used_tokens: int | None
    remaining_tokens: int | None


class CabinetService:
    def __init__(
        self,
        *,
        user_service: UserService,
        access_repository: AccessGrantRepository,
        subscription_service: SubscriptionService,
        default_provider_code: str = "openai",
    ) -> None:
        self._user_service = user_service
        self._access_repository = access_repository
        self._subscription_service = subscription_service
        self._default_provider_code = default_provider_code

    def should_show_for_text(self, message_text: str | None) -> bool:
        if not message_text:
            return False

        normalized = _normalize_action_text(message_text)
        return normalized in {
            "личный кабинет",
            "кабинет",
            "мой кабинет",
            "меню",
            "profile",
            "вернуться в личный кабинет",
            "в кабинет",
        }

    def build_text_for_user_id(self, *, user_id: int) -> str:
        snapshot = self.get_snapshot(user_id=user_id)
        status_icon = "🟩" if snapshot.access_active else "🟥"
        plan_title = snapshot.plan_title or "Free"
        remaining_text = _format_token_value(snapshot.remaining_tokens)
        lines = [
            "AI BOT",
            "",
            f"{status_icon} Ваш ID: {snapshot.vk_user_id}",
            "",
            f"💎 Подписка: {plan_title}",
            f"🔹 Баланс: {remaining_text} токенов",
            f"🤖 Активный ИИ: {snapshot.provider_title}",
            "",
            "🚀 Что умеет ИИ:",
            "– Ответы на вопросы",
            "– Решение задач по фото",
            "– Помощь с текстами",
            "",
            "💎 Открой полный доступ:",
            "✔️ Больше ответов без ограничений",
            "✔️ Быстрая обработка без ожидания",
            "✔️ Дополнительные функции",
        ]

        if snapshot.plan_title is not None:
            lines.extend(
                [
                    "",
                    f"📦 Лимит тарифа: {_format_token_value(snapshot.included_tokens)} токенов",
                    f"✍️ Уже использовано: {_format_token_value(snapshot.used_tokens)}",
                ]
            )

        return "\n".join(lines)

    def build_instruction_text(self) -> str:
        return "\n".join(
            [
                "📘 Инструкция",
                "",
                "Как пользоваться:",
                "– Вопрос (текст/голос) — просто пиши или отправь голосовое",
                "– Решить задачу по фото — отправь фото",
                "",
                "Поддержка: @zhigunov3",
            ]
        )

    def build_support_text(self) -> str:
        return "\n".join(
            [
                "🆘 Поддержка",
                "",
                "Если что-то не работает или нужен быстрый ответ, напишите:",
                "@zhigunov3",
            ]
        )

    def should_show_instruction_for_text(self, message_text: str | None) -> bool:
        if not message_text:
            return False

        normalized = _normalize_action_text(message_text)
        return normalized in {"инструкция", "как пользоваться", "help"}

    def should_show_support_for_text(self, message_text: str | None) -> bool:
        if not message_text:
            return False

        normalized = _normalize_action_text(message_text)
        return normalized in {"поддержка", "support"}

    def should_show_plans_for_text(self, message_text: str | None) -> bool:
        if not message_text:
            return False

        normalized = _normalize_action_text(message_text)
        return normalized in {"тарифы", "подписка", "подписки", "апгрейд"}

    def build_plans_text(self) -> str:
        return render_subscription_plans_text()

    def get_plan_code_from_text(self, message_text: str | None) -> str | None:
        if not message_text:
            return None

        plan = find_subscription_plan_by_button_text(message_text)
        if plan is None:
            return None
        return plan.code

    def build_plan_detail_text(
        self,
        *,
        plan_code: str,
        payment_url: str | None = None,
        is_test: bool = False,
    ) -> str:
        return render_subscription_plan_detail_text(
            plan_code,
            payment_url=payment_url,
            is_test=is_test,
        )

    def get_plan_image_path(self, *, plan_code: str) -> str:
        return get_subscription_plan_image_path(plan_code)

    def get_snapshot(self, *, user_id: int) -> CabinetSnapshot:
        user = self._user_service.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User not found: {user_id}")

        access_active = self._access_repository.has_grant_for_user_id(user_id)
        subscription = self._subscription_service.get_subscription(user_id=user_id)
        provider_code = user.selected_provider or self._default_provider_code
        provider_title = get_provider_option(provider_code).title

        if subscription is None:
            return CabinetSnapshot(
                user_id=user.id,
                vk_user_id=user.vk_user_id,
                access_active=access_active,
                provider_title=provider_title,
                plan_title=None,
                included_tokens=None,
                used_tokens=None,
                remaining_tokens=None,
            )

        try:
            plan = get_subscription_plan(subscription.plan_code)
        except ValueError:
            remaining_tokens = max(subscription.included_tokens - subscription.used_tokens, 0)
            return CabinetSnapshot(
                user_id=user.id,
                vk_user_id=user.vk_user_id,
                access_active=access_active or remaining_tokens > 0,
                provider_title=provider_title,
                plan_title=subscription.plan_code.title(),
                included_tokens=subscription.included_tokens,
                used_tokens=subscription.used_tokens,
                remaining_tokens=remaining_tokens,
            )

        remaining_tokens = max(subscription.included_tokens - subscription.used_tokens, 0)
        return CabinetSnapshot(
            user_id=user.id,
            vk_user_id=user.vk_user_id,
            access_active=access_active or remaining_tokens > 0,
            provider_title=provider_title,
            plan_title=plan.title,
            included_tokens=subscription.included_tokens,
            used_tokens=subscription.used_tokens,
            remaining_tokens=remaining_tokens,
        )


def _format_token_value(value: int | None) -> str:
    if value is None:
        return "0"

    return f"{value:,}".replace(",", " ")


def _normalize_action_text(value: str) -> str:
    normalized = re.sub(r"[^\w\s]+", " ", value.casefold(), flags=re.UNICODE)
    return " ".join(normalized.split())
