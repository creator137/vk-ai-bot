from __future__ import annotations

import logging

from app.vk_transport.outward_reactions import VkOutwardReactionPlan
from app.vk_transport.schemas import NormalizedVkEvent
from app.vk_transport.vk_api import VkMessagesApi

logger = logging.getLogger(__name__)


def deliver_planned_vk_reaction(
    event: NormalizedVkEvent,
    reaction: VkOutwardReactionPlan,
    *,
    messages_api: VkMessagesApi,
) -> None:
    if reaction.action == "none":
        return

    if event.peer_id is None:
        logger.warning(
            "VK outward reaction delivery skipped: type=%s event_id=%s reason=missing_peer_id",
            event.event_type,
            event.event_id,
        )
        return

    if not reaction.text:
        logger.warning(
            "VK outward reaction delivery skipped: type=%s event_id=%s reason=missing_text",
            event.event_type,
            event.event_id,
        )
        return

    messages_api.send_text_message(
        peer_id=event.peer_id,
        text=reaction.text,
        keyboard=reaction.keyboard,
        image_path=reaction.image_path,
    )
    logger.info(
        (
            "VK outward reaction delivered: type=%s event_id=%s "
            "action=%s peer_id=%s"
        ),
        event.event_type,
        event.event_id,
        reaction.action,
        event.peer_id,
    )
