from __future__ import annotations

import logging

import dramatiq
import httpx

from app.ai.provider import OpenAIProviderError, OpenAIResponsesTextProvider
from app.core.config import get_settings
from app.vk_transport.delivery import deliver_planned_vk_reaction
from app.vk_transport.outward_reactions import VkOutwardReactionPlan
from app.vk_transport.schemas import NormalizedVkEvent
from app.vk_transport.vk_api import VkApiError, VkMessagesApi

logger = logging.getLogger(__name__)


@dramatiq.actor(queue_name="accepted_requests")
def process_vk_accepted_text_request(peer_id: int, text: str) -> None:
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning(
            "Accepted VK text request skipped: peer_id=%s reason=missing_openai_api_key",
            peer_id,
        )
        return

    if not settings.vk_outbound_token:
        logger.warning(
            "Accepted VK text request skipped: peer_id=%s reason=missing_vk_outbound_token",
            peer_id,
        )
        return

    provider = OpenAIResponsesTextProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )
    messages_api = VkMessagesApi(
        token=settings.vk_outbound_token,
        api_version=settings.vk_api_version,
    )
    try:
        run_accepted_vk_text_request(
            peer_id=peer_id,
            text=text,
            provider=provider,
            messages_api=messages_api,
        )
    except (OpenAIProviderError, VkApiError, httpx.HTTPError) as error:
        logger.warning(
            "Accepted VK text request failed: peer_id=%s error=%s",
            peer_id,
            str(error),
        )


def run_accepted_vk_text_request(
    *,
    peer_id: int,
    text: str,
    provider: OpenAIResponsesTextProvider,
    messages_api: VkMessagesApi,
) -> None:
    reply_text = provider.generate_text(text)
    deliver_planned_vk_reaction(
        _build_reply_event(peer_id=peer_id, text=text),
        VkOutwardReactionPlan(action="send_text", text=reply_text),
        messages_api=messages_api,
    )
    logger.info("Accepted VK text request completed: peer_id=%s", peer_id)


def _build_reply_event(*, peer_id: int, text: str) -> NormalizedVkEvent:
    return NormalizedVkEvent(
        event_type="message_new",
        group_id=1,
        peer_id=peer_id,
        payload={"message": {"text": text}},
    )
