from __future__ import annotations

import logging
from typing import Any, Protocol

from fastapi import HTTPException, status
import httpx
from sqlalchemy.orm import Session

from app.application.accepted_dispatch import dispatch_accepted_vk_event
from app.application.vk_events import build_vk_event_application_handler
from app.application.request_outcomes import RequestOutcome
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.vk_transport.delivery import deliver_planned_vk_reaction
from app.vk_transport.outcome_consumer import OutcomeConsumption, consume_request_outcome
from app.vk_transport.outward_reactions import (
    VkOutwardReactionPlan,
    plan_vk_outward_reaction,
)
from app.vk_transport.schemas import NormalizedVkEvent, VkCallbackPayload
from app.vk_transport.vk_api import VkMessagesApi, VkApiError

logger = logging.getLogger(__name__)


class VkEventHandoff(Protocol):
    def handle(self, event: NormalizedVkEvent) -> RequestOutcome:
        """Accept a normalized VK event for future service-layer processing."""


class ApplicationVkEventHandoff:
    def handle(self, event: NormalizedVkEvent) -> RequestOutcome:
        logger.info(
            "VK event accepted: type=%s event_id=%s actor_id=%s peer_id=%s",
            event.event_type,
            event.event_id,
            event.actor_id,
            event.peer_id,
        )
        session_factory = get_session_factory()
        with session_factory() as session:
            outcome = _dispatch_to_application(session, event)
        consumption = consume_request_outcome(outcome)
        _handle_consumed_outcome(event, outcome, consumption)
        _dispatch_accepted_event(event, outcome, consumption)
        reaction = _plan_outward_reaction(event, outcome, consumption)
        _deliver_outward_reaction(event, reaction)
        return outcome


def _dispatch_to_application(session: Session, event: NormalizedVkEvent) -> RequestOutcome:
    handler = build_vk_event_application_handler(session)
    return handler.handle(event)


def _handle_consumed_outcome(
    event: NormalizedVkEvent,
    outcome: RequestOutcome,
    consumption: OutcomeConsumption,
) -> None:
    if consumption.state == "ignored":
        logger.info(
            "VK event branch ignored: type=%s event_id=%s reason=%s",
            event.event_type,
            event.event_id,
            outcome.reason,
        )
        return

    if consumption.state == "halted":
        logger.info(
            "VK event branch halted: type=%s event_id=%s reason=%s user_id=%s",
            event.event_type,
            event.event_id,
            outcome.reason,
            outcome.user_id,
        )
        return

    if consumption.state == "completed":
        logger.info(
            "VK event branch completed: type=%s event_id=%s reason=%s user_id=%s",
            event.event_type,
            event.event_id,
            outcome.reason,
            outcome.user_id,
        )
        return

    logger.info(
        (
            "VK event branch ready for next stage: type=%s event_id=%s "
            "reason=%s user_id=%s"
        ),
        event.event_type,
        event.event_id,
        outcome.reason,
        outcome.user_id,
    )


def _plan_outward_reaction(
    event: NormalizedVkEvent,
    outcome: RequestOutcome,
    consumption: OutcomeConsumption,
) -> VkOutwardReactionPlan:
    handled_text = _extract_string(event.payload, "handled_text")
    handled_view = _extract_string(event.payload, "handled_view")
    handled_payment_url = _extract_string(event.payload, "handled_payment_url")
    handled_image_path = _extract_string(event.payload, "handled_image_path")
    reaction = plan_vk_outward_reaction(
        consumption,
        outcome_reason=outcome.reason,
        handled_text=handled_text,
        handled_view=handled_view,
        handled_payment_url=handled_payment_url,
        handled_image_path=handled_image_path,
    )
    if reaction.action == "none":
        logger.info(
            "VK outward reaction not planned: type=%s event_id=%s branch=%s",
            event.event_type,
            event.event_id,
            consumption.state,
        )
        return reaction

    logger.info(
        (
            "VK outward reaction planned: type=%s event_id=%s branch=%s "
            "action=%s text=%s"
        ),
        event.event_type,
        event.event_id,
        consumption.state,
        reaction.action,
        reaction.text,
    )
    return reaction


def _dispatch_accepted_event(
    event: NormalizedVkEvent,
    outcome: RequestOutcome,
    consumption: OutcomeConsumption,
) -> None:
    if consumption.state != "ready_for_next_stage":
        return

    if outcome.user_id is None:
        return

    event.payload["user_id"] = outcome.user_id
    dispatch_accepted_vk_event(event)


def _deliver_outward_reaction(
    event: NormalizedVkEvent,
    reaction: VkOutwardReactionPlan,
) -> None:
    if reaction.action == "none":
        return

    settings = get_settings()
    if not settings.vk_outbound_token:
        logger.warning(
            "VK outward reaction delivery skipped: type=%s event_id=%s reason=missing_outbound_token",
            event.event_type,
            event.event_id,
        )
        return

    messages_api = VkMessagesApi(
        token=settings.vk_outbound_token,
        api_version=settings.vk_api_version,
    )
    try:
        deliver_planned_vk_reaction(
            event,
            reaction,
            messages_api=messages_api,
        )
    except (VkApiError, HTTPException, httpx.HTTPError) as error:
        logger.warning(
            "VK outward reaction delivery failed: type=%s event_id=%s error=%s",
            event.event_type,
            event.event_id,
            str(error),
        )


_handoff = ApplicationVkEventHandoff()


def get_vk_event_handoff() -> VkEventHandoff:
    return _handoff


def ensure_vk_callback_secret(payload_secret: str | None, expected_secret: str | None) -> None:
    if expected_secret is None:
        return

    if payload_secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid VK callback secret",
        )


def normalize_vk_event(payload: VkCallbackPayload) -> NormalizedVkEvent:
    actor_id = _extract_actor_id(payload.object)
    peer_id = _extract_int(payload.object, "peer_id")
    occurred_at = _extract_int(payload.object, "date")

    message = _extract_mapping(payload.object.get("message"))
    if message:
        actor_id = actor_id or _extract_int(message, "from_id")
        peer_id = peer_id or _extract_int(message, "peer_id")
        occurred_at = occurred_at or _extract_int(message, "date")

    return NormalizedVkEvent(
        event_type=payload.type,
        group_id=payload.group_id,
        event_id=payload.event_id,
        actor_id=actor_id,
        peer_id=peer_id,
        occurred_at=occurred_at,
        payload=payload.object,
    )


def _extract_actor_id(payload_object: dict[str, Any]) -> int | None:
    for key in ("from_id", "user_id"):
        value = _extract_int(payload_object, key)
        if value is not None:
            return value
    return None


def _extract_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, int):
        return value
    return None


def _extract_mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    return None


def _extract_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    return None

