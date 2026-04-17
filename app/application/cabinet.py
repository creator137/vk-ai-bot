from __future__ import annotations

from dataclasses import dataclass
import re

from app.access.repository import AccessGrantRepository
from app.ai.provider_catalog import get_provider_option
from app.subscriptions.catalog import (
    find_subscription_plan_by_button_text,
    get_subscription_plan,
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
    ) -> None:
        self._user_service = user_service
        self._access_repository = access_repository
        self._subscription_service = subscription_service

    def should_show_for_text(self, message_text: str | None) -> bool:
        if not message_text:
            return False

        normalized = _normalize_action_text(message_text)
        return normalized in {
            "личный кабинет",
            "кабинет",
            "мой кабинет",
            "profile",
            "вернуться в личный кабинет",
            "в кабинет",
        }

    def build_text_for_user_id(self, *, user_id: int) -> str:
        snapshot = self.get_snapshot(user_id=user_id)
        access_text = "Активен" if snapshot.access_active else "Не активирован"
        lines = [
            "AI BOT",
            "",
            "✨ Личный кабинет",
            "Умный помощник для идей, ответов и работы прямо в сообщениях VK.",
            "",
            "Профиль",
            f"• ID: {snapshot.vk_user_id}",
            f"• Доступ: {access_text}",
            f"• Активная модель: {snapshot.provider_title}",
        ]

        if snapshot.plan_title is None:
            lines.extend(
                [
                    "• Тариф: Free",
                    "",
                    "Баланс",
                    "• Лимит пока не подключён",
                    "• После активации появится личный запас для общения",
                    "",
                    "Что можно сделать",
                    "• выбрать удобную нейросеть",
                    "• открыть тарифы",
                    "• активировать доступ и начать диалог",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "Баланс",
                    f"• Тариф: {snapshot.plan_title}",
                    "• Осталось: "
                    f"{_format_token_value(snapshot.remaining_tokens)} из "
                    f"{_format_token_value(snapshot.included_tokens)}",
                    "• Баланс зависит от объёма переписки",
                    "",
                    "Что можно сделать",
                    "• продолжить диалог с выбранной моделью",
                    "• переключиться на другую нейросеть",
                    "• открыть тарифы и сравнить планы",
                ]
            )
        return "\n".join(lines)

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

    def get_snapshot(self, *, user_id: int) -> CabinetSnapshot:
        user = self._user_service.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User not found: {user_id}")

        access_active = self._access_repository.has_grant_for_user_id(user_id)
        subscription = self._subscription_service.get_subscription(user_id=user_id)
        provider_code = user.selected_provider or "openai"
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

        plan = get_subscription_plan(subscription.plan_code)
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
