from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.access.repository import AccessGrantRepository
from app.access.service import AccessDecision, AccessService
from app.ai.provider_catalog import find_provider_option_by_button_text, get_provider_option
from app.application.cabinet import CabinetService
from app.application.payments import RobokassaPaymentInitHandler, build_robokassa_payment_init_handler
from app.application.provider_selection import ProviderSelectionService
from app.application.request_outcomes import RequestOutcome
from app.core.config import Settings, get_settings
from app.payments.robokassa import RobokassaError
from app.subscriptions.service import SubscriptionIssue, SubscriptionService
from app.users.service import UserService
from app.vk_transport.keyboards import build_dialog_menu_keyboard
from app.vk_transport.schemas import NormalizedVkEvent
from app.vk_transport.vk_api import VkApiError, VkMessagesApi

logger = logging.getLogger(__name__)


class VkEventApplicationHandler:
    def __init__(
        self,
        user_service: UserService,
        subscription_service: SubscriptionService,
        access_service: AccessService,
        provider_selection_service: ProviderSelectionService,
        cabinet_service: CabinetService,
        payment_init_handler: RobokassaPaymentInitHandler,
        settings: Settings,
        notify_daily_bonus: Callable[[int, SubscriptionIssue], None] | None = None,
    ) -> None:
        self._user_service = user_service
        self._subscription_service = subscription_service
        self._access_service = access_service
        self._provider_selection_service = provider_selection_service
        self._cabinet_service = cabinet_service
        self._payment_init_handler = payment_init_handler
        self._settings = settings
        self._notify_daily_bonus = notify_daily_bonus

    def handle(self, event: NormalizedVkEvent) -> RequestOutcome:
        if event.actor_id is None:
            outcome = RequestOutcome(status="skipped", reason="missing_actor_id")
            logger.info(
                "VK event skipped: type=%s event_id=%s reason=%s",
                event.event_type,
                event.event_id,
                outcome.reason,
            )
            return outcome

        user = self._user_service.find_or_create_by_vk_user_id(event.actor_id)
        self._issue_and_notify_daily_bonus_if_needed(event=event, user_id=user.id, vk_user_id=user.vk_user_id)
        message_text = _extract_message_text(event.payload)
        button_action = _extract_button_action(event.payload)

        provider_selection = None
        requested_provider_code = _resolve_requested_provider_code(
            button_action=button_action,
            message_text=message_text,
        )
        if requested_provider_code is not None:
            if not _is_provider_available(
                settings=self._settings,
                provider_code=requested_provider_code,
            ):
                provider_title = get_provider_option(requested_provider_code).title
                event.payload["handled_text"] = (
                    f"⚠️ {provider_title} сейчас недоступен.\n"
                    "Провайдер не настроен в runtime. Выберите другой ИИ."
                )
                event.payload["handled_view"] = "cabinet"
                outcome = RequestOutcome(
                    status="handled",
                    reason="provider_unavailable",
                    user_id=user.id,
                )
                logger.info(
                    "VK provider unavailable: type=%s event_id=%s user_id=%s vk_user_id=%s provider=%s",
                    event.event_type,
                    event.event_id,
                    user.id,
                    user.vk_user_id,
                    requested_provider_code,
                )
                return outcome

            provider_selection = self._provider_selection_service.select_provider(
                user_id=user.id,
                provider_code=requested_provider_code,
            )
        if provider_selection is not None:
            event.payload["handled_text"] = (
                f"✨ Теперь отвечаю через {provider_selection.provider_title}\n"
                "Просто отправьте следующее сообщение."
            )
            event.payload["handled_view"] = "cabinet"
            outcome = RequestOutcome(
                status="handled",
                reason="provider_selected",
                user_id=user.id,
            )
            logger.info(
                (
                    "VK provider selected: type=%s event_id=%s user_id=%s "
                    "vk_user_id=%s provider=%s"
                ),
                event.event_type,
                event.event_id,
                user.id,
                user.vk_user_id,
                provider_selection.provider_code,
            )
            return outcome

        if button_action.get("type") == "cabinet_open" or self._cabinet_service.should_show_for_text(message_text):
            event.payload["handled_text"] = self._cabinet_service.build_text_for_user_id(
                user_id=user.id,
            )
            event.payload["handled_view"] = "cabinet"
            outcome = RequestOutcome(
                status="handled",
                reason="cabinet_shown",
                user_id=user.id,
            )
            logger.info(
                "VK cabinet shown: type=%s event_id=%s user_id=%s vk_user_id=%s",
                event.event_type,
                event.event_id,
                user.id,
                user.vk_user_id,
            )
            return outcome

        if button_action.get("type") == "instruction_open" or self._cabinet_service.should_show_instruction_for_text(message_text):
            event.payload["handled_text"] = self._cabinet_service.build_instruction_text()
            event.payload["handled_view"] = "cabinet"
            outcome = RequestOutcome(
                status="handled",
                reason="instruction_shown",
                user_id=user.id,
            )
            logger.info(
                "VK instruction shown: type=%s event_id=%s user_id=%s vk_user_id=%s",
                event.event_type,
                event.event_id,
                user.id,
                user.vk_user_id,
            )
            return outcome

        if button_action.get("type") == "support_open" or self._cabinet_service.should_show_support_for_text(message_text):
            event.payload["handled_text"] = self._cabinet_service.build_support_text()
            event.payload["handled_view"] = "cabinet"
            outcome = RequestOutcome(
                status="handled",
                reason="support_shown",
                user_id=user.id,
            )
            logger.info(
                "VK support shown: type=%s event_id=%s user_id=%s vk_user_id=%s",
                event.event_type,
                event.event_id,
                user.id,
                user.vk_user_id,
            )
            return outcome

        if button_action.get("type") == "plans_open" or self._cabinet_service.should_show_plans_for_text(message_text):
            event.payload["handled_text"] = self._cabinet_service.build_plans_text()
            event.payload["handled_view"] = "plans"
            outcome = RequestOutcome(
                status="handled",
                reason="plans_shown",
                user_id=user.id,
            )
            logger.info(
                "VK plans shown: type=%s event_id=%s user_id=%s vk_user_id=%s",
                event.event_type,
                event.event_id,
                user.id,
                user.vk_user_id,
            )
            return outcome

        plan_code = button_action.get("plan")
        if not isinstance(plan_code, str):
            plan_code = self._cabinet_service.get_plan_code_from_text(message_text)
        if plan_code is not None:
            payment_url = None
            is_test_payment = False
            try:
                payment = self._payment_init_handler.create_for_vk_user_id(
                    vk_user_id=user.vk_user_id,
                    plan_code=plan_code,
                )
            except RobokassaError:
                payment = None
            else:
                payment_url = payment.payment_url
                is_test_payment = payment.is_test

            event.payload["handled_text"] = self._cabinet_service.build_plan_detail_text(
                plan_code=plan_code,
                payment_url=payment_url,
                is_test=is_test_payment,
            )
            event.payload["handled_view"] = "plan_detail"
            event.payload["handled_image_path"] = self._cabinet_service.get_plan_image_path(
                plan_code=plan_code,
            )
            if payment_url:
                event.payload["handled_payment_url"] = payment_url
            outcome = RequestOutcome(
                status="handled",
                reason="plan_preview_shown",
                user_id=user.id,
            )
            logger.info(
                "VK plan preview shown: type=%s event_id=%s user_id=%s vk_user_id=%s plan=%s",
                event.event_type,
                event.event_id,
                user.id,
                user.vk_user_id,
                plan_code,
            )
            return outcome

        decision = self._access_service.decide_for_user_id(user.id)
        outcome = _map_access_decision_to_outcome(user.id, decision)
        logger.info(
            (
                "VK event outcome decided: type=%s event_id=%s user_id=%s "
                "vk_user_id=%s status=%s reason=%s"
            ),
            event.event_type,
            event.event_id,
            user.id,
            user.vk_user_id,
            outcome.status,
            outcome.reason,
        )
        return outcome

    def _issue_and_notify_daily_bonus_if_needed(
        self,
        *,
        event: NormalizedVkEvent,
        user_id: int,
        vk_user_id: int,
    ) -> None:
        issued = self._subscription_service.issue_daily_exhausted_bonus_for_user_id(
            user_id=user_id,
        )
        if issued is None:
            return

        logger.info(
            (
                "VK daily bonus issued: type=%s event_id=%s user_id=%s "
                "vk_user_id=%s plan=%s included_tokens=%s used_tokens=%s"
            ),
            event.event_type,
            event.event_id,
            user_id,
            vk_user_id,
            issued.plan_code,
            issued.included_tokens,
            issued.used_tokens,
        )

        if self._notify_daily_bonus is None:
            return

        try:
            self._notify_daily_bonus(vk_user_id, issued)
        except (VkApiError, httpx.HTTPError) as error:
            logger.warning(
                "VK daily bonus notification failed: type=%s event_id=%s user_id=%s error=%s",
                event.event_type,
                event.event_id,
                user_id,
                str(error),
            )
            return

        logger.info(
            "VK daily bonus notification sent: type=%s event_id=%s user_id=%s vk_user_id=%s",
            event.event_type,
            event.event_id,
            user_id,
            vk_user_id,
        )


def _map_access_decision_to_outcome(
    user_id: int,
    decision: AccessDecision,
) -> RequestOutcome:
    if decision.allowed:
        return RequestOutcome(
            status="accepted",
            reason="access_allowed",
            user_id=user_id,
        )

    return RequestOutcome(
        status="denied",
        reason=decision.reason,
        user_id=user_id,
    )


def build_vk_event_application_handler(session: Session) -> VkEventApplicationHandler:
    settings = get_settings()
    user_service = UserService(session=session)
    access_repository = AccessGrantRepository(session)
    subscription_service = SubscriptionService(session=session)
    provider_selection_service = ProviderSelectionService(user_service=user_service)
    payment_init_handler = build_robokassa_payment_init_handler(session, settings)
    cabinet_service = CabinetService(
        user_service=user_service,
        access_repository=access_repository,
        subscription_service=subscription_service,
        default_provider_code=settings.ai_provider,
    )
    access_service = AccessService(
        repository=access_repository,
        subscription_service=subscription_service,
    )
    return VkEventApplicationHandler(
        user_service=user_service,
        subscription_service=subscription_service,
        access_service=access_service,
        provider_selection_service=provider_selection_service,
        cabinet_service=cabinet_service,
        payment_init_handler=payment_init_handler,
        settings=settings,
        notify_daily_bonus=_build_daily_bonus_notifier(settings=settings),
    )


def _extract_message_text(payload: dict[str, Any]) -> str | None:
    message = payload.get("message")
    if not isinstance(message, dict):
        return None

    text = message.get("text")
    if not isinstance(text, str):
        return None

    stripped = text.strip()
    if not stripped:
        return None

    return stripped


def _extract_button_action(payload: dict[str, Any]) -> dict[str, Any]:
    message = payload.get("message")
    if not isinstance(message, dict):
        return {}

    raw_payload = message.get("payload")
    if not isinstance(raw_payload, str) or not raw_payload.strip():
        return {}

    try:
        decoded = json.loads(raw_payload)
    except json.JSONDecodeError:
        return {}

    if not isinstance(decoded, dict):
        return {}

    return decoded


def _resolve_requested_provider_code(
    *,
    button_action: dict[str, Any],
    message_text: str | None,
) -> str | None:
    if button_action.get("type") == "provider_select":
        provider_code = button_action.get("provider")
        if not isinstance(provider_code, str):
            return None
        try:
            return get_provider_option(provider_code).code
        except ValueError:
            return None

    if not message_text:
        return None

    option = find_provider_option_by_button_text(message_text)
    if option is None:
        return None
    return option.code


def _is_provider_available(*, settings: Settings, provider_code: str) -> bool:
    if provider_code == "openai":
        return bool(settings.openai_api_key)
    if provider_code == "gemini":
        return bool(settings.gemini_api_key)
    if provider_code == "claude":
        return bool(settings.claude_api_key)
    return False


def _build_daily_bonus_notifier(
    *,
    settings: Settings,
) -> Callable[[int, SubscriptionIssue], None] | None:
    if not settings.vk_outbound_token:
        return None

    messages_api = VkMessagesApi(
        token=settings.vk_outbound_token,
        api_version=settings.vk_api_version,
    )

    def notify(vk_user_id: int, issued: SubscriptionIssue) -> None:
        tokens_text = f"{issued.included_tokens:,}".replace(",", " ")
        messages_api.send_text_message(
            peer_id=vk_user_id,
            text=(
                f"Вам начислены новые ежедневные {tokens_text} токенов.\n"
                "Бесплатный дневной баланс обновлён.\n"
                "Можете продолжать диалог."
            ),
            keyboard=build_dialog_menu_keyboard(),
            image_path=None,
        )

    return notify
