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
    photo_urls = _extract_photo_urls(message.get("attachments"))
    if text is None and not photo_urls:
        logger.info(
            "Accepted VK dispatch skipped: type=%s event_id=%s reason=missing_text_or_photo",
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

    user_id = _extract_user_id(event)
    if user_id is None:
        logger.info(
            "Accepted VK dispatch skipped: type=%s event_id=%s reason=missing_user_id",
            event.event_type,
            event.event_id,
        )
        return

    if photo_urls:
        _get_accepted_photo_request_actor().send(user_id, event.peer_id, text, photo_urls)
        logger.info(
            (
                "Accepted VK photo dispatch enqueued: type=%s event_id=%s "
                "user_id=%s peer_id=%s photo_count=%s"
            ),
            event.event_type,
            event.event_id,
            user_id,
            event.peer_id,
            len(photo_urls),
        )
        return

    _get_accepted_request_actor().send(user_id, event.peer_id, text)
    logger.info(
        "Accepted VK dispatch enqueued: type=%s event_id=%s user_id=%s peer_id=%s",
        event.event_type,
        event.event_id,
        user_id,
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


def _extract_user_id(event: NormalizedVkEvent) -> int | None:
    value = event.payload.get("user_id")
    if isinstance(value, int) and value > 0:
        return value
    return None


def _extract_photo_urls(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    urls: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "photo":
            continue

        photo = _extract_mapping(item.get("photo"))
        if photo is None:
            continue

        url = _extract_photo_url(photo)
        if url is not None:
            urls.append(url)

    return urls


def _extract_photo_url(photo: dict[str, Any]) -> str | None:
    orig_photo = _extract_mapping(photo.get("orig_photo"))
    if orig_photo is not None:
        url = orig_photo.get("url")
        if isinstance(url, str) and url:
            return url

    sizes = photo.get("sizes")
    if not isinstance(sizes, list):
        return None

    best_url: str | None = None
    best_area = -1
    for item in sizes:
        if not isinstance(item, dict):
            continue

        url = item.get("url")
        if not isinstance(url, str) or not url:
            continue

        width = item.get("width")
        height = item.get("height")
        area = width * height if isinstance(width, int) and isinstance(height, int) else 0
        if area >= best_area:
            best_area = area
            best_url = url

    return best_url


def _get_accepted_request_actor():
    ensure_worker_broker_configured()

    from app.workers.accepted_requests import process_vk_accepted_text_request

    return process_vk_accepted_text_request


def _get_accepted_photo_request_actor():
    ensure_worker_broker_configured()

    from app.workers.accepted_requests import process_vk_accepted_photo_request

    return process_vk_accepted_photo_request
