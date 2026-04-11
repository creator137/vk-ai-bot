from __future__ import annotations

import logging
from typing import Any

from app.vk_transport.schemas import NormalizedVkEvent
from app.workers.bootstrap import ensure_worker_broker_configured

logger = logging.getLogger(__name__)


def dispatch_accepted_vk_event(event: NormalizedVkEvent) -> None:
    if event.event_type != "message_new":
        logger.info(
            "Accepted VK dispatch skipped: type=%s event_id=%s reason=unsupported_event_type",
            event.event_type,
            event.event_id,
        )
        return

    message = _extract_mapping(event.payload.get("message"))
    if message is None:
        logger.info(
            "Accepted VK dispatch skipped: type=%s event_id=%s reason=missing_message_payload",
            event.event_type,
            event.event_id,
        )
        return

    text = _extract_text(message.get("text"))
    if text is None:
        logger.info(
            "Accepted VK dispatch skipped: type=%s event_id=%s reason=missing_text",
            event.event_type,
            event.event_id,
        )
        return

    if event.peer_id is None:
        logger.info(
            "Accepted VK dispatch skipped: type=%s event_id=%s reason=missing_peer_id",
            event.event_type,
            event.event_id,
        )
        return

    _get_accepted_request_actor().send(event.peer_id, text)
    logger.info(
        "Accepted VK dispatch enqueued: type=%s event_id=%s peer_id=%s",
        event.event_type,
        event.event_id,
        event.peer_id,
    )


def _extract_mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    return None


def _extract_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    return text


def _get_accepted_request_actor():
    ensure_worker_broker_configured()

    from app.workers.accepted_requests import process_vk_accepted_text_request

    return process_vk_accepted_text_request
