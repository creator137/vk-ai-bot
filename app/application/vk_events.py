from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.access.repository import AccessGrantRepository
from app.access.service import AccessDecision, AccessService
from app.application.cabinet import CabinetService
from app.application.payments import RobokassaPaymentInitHandler, build_robokassa_payment_init_handler
from app.application.provider_selection import ProviderSelectionService
from app.application.request_outcomes import RequestOutcome
from app.core.config import get_settings
from app.payments.robokassa import RobokassaError
from app.subscriptions.service import SubscriptionService
from app.users.service import UserService
from app.vk_transport.schemas import NormalizedVkEvent

logger = logging.getLogger(__name__)


class VkEventApplicationHandler:
    def __init__(
        self,
        user_service: UserService,
        access_service: AccessService,
        provider_selection_service: ProviderSelectionService,
        cabinet_service: CabinetService,
        payment_init_handler: RobokassaPaymentInitHandler,
    ) -> None:
        self._user_service = user_service
        self._access_service = access_service
        self._provider_selection_service = provider_selection_service
        self._cabinet_service = cabinet_service
        self._payment_init_handler = payment_init_handler

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
        message_text = _extract_message_text(event.payload)
        button_action = _extract_button_action(event.payload)

        provider_selection = None
        if button_action.get("type") == "provider_select":
            provider_code = button_action.get("provider")
            if isinstance(provider_code, str):
                provider_selection = self._provider_selection_service.select_provider(
                    user_id=user.id,
                    provider_code=provider_code,
                )
        else:
            provider_selection = self._provider_selection_service.handle_message_text(
                user_id=user.id,
                message_text=message_text,
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
        reason="access_denied",
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
    )
    access_service = AccessService(
        repository=access_repository,
        subscription_service=subscription_service,
    )
    return VkEventApplicationHandler(
        user_service=user_service,
        access_service=access_service,
        provider_selection_service=provider_selection_service,
        cabinet_service=cabinet_service,
        payment_init_handler=payment_init_handler,
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
