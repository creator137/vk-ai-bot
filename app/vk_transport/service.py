from __future__ import annotations

import logging
from typing import Any, Protocol

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.application.vk_events import build_vk_event_application_handler
from app.application.request_outcomes import RequestOutcome
from app.db.session import get_session_factory
from app.vk_transport.outcome_consumer import consume_request_outcome
from app.vk_transport.schemas import NormalizedVkEvent, VkCallbackPayload

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
        logger.info(
            (
                "VK event flow completed: type=%s event_id=%s status=%s "
                "reason=%s user_id=%s completion=%s"
            ),
            event.event_type,
            event.event_id,
            outcome.status,
            outcome.reason,
            outcome.user_id,
            consumption.state,
        )
        return outcome


def _dispatch_to_application(session: Session, event: NormalizedVkEvent) -> RequestOutcome:
    handler = build_vk_event_application_handler(session)
    return handler.handle(event)


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

