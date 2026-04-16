from __future__ import annotations

import logging
from collections.abc import Callable

import dramatiq
import httpx

from app.ai.provider import (
    ClaudeMessagesTextProvider,
    ClaudeProviderError,
    GeminiGenerateContentProvider,
    GeminiProviderError,
    OpenAIProviderError,
    OpenAIResponsesTextProvider,
    TextGenerationProvider,
)
from app.ai.provider_catalog import get_provider_option
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.requests.service import AcceptedRequestPersistenceService
from app.subscriptions.service import SubscriptionService
from app.users.service import UserService
from app.vk_transport.delivery import deliver_planned_vk_reaction
from app.vk_transport.keyboards import build_dialog_menu_keyboard
from app.vk_transport.outward_reactions import VkOutwardReactionPlan
from app.vk_transport.schemas import NormalizedVkEvent
from app.vk_transport.vk_api import VkApiError, VkMessagesApi

logger = logging.getLogger(__name__)


@dramatiq.actor(queue_name="accepted_requests")
def process_vk_accepted_text_request(user_id: int, peer_id: int, text: str) -> None:
    settings = get_settings()
    if not settings.vk_outbound_token:
        logger.warning(
            "Accepted VK text request skipped: peer_id=%s reason=missing_vk_outbound_token",
            peer_id,
        )
        return

    provider_code = _resolve_provider_code_for_user(user_id=user_id, fallback=settings.ai_provider)
    provider = _build_text_provider(settings, peer_id=peer_id, provider_code=provider_code)
    if provider is None:
        return

    messages_api = VkMessagesApi(
        token=settings.vk_outbound_token,
        api_version=settings.vk_api_version,
    )
    try:
        run_accepted_vk_text_request(
            user_id=user_id,
            peer_id=peer_id,
            text=text,
            provider=provider,
            messages_api=messages_api,
            persist_exchange=_persist_accepted_text_exchange,
        )
    except (
        OpenAIProviderError,
        GeminiProviderError,
        ClaudeProviderError,
        VkApiError,
        httpx.HTTPError,
    ) as error:
        logger.warning(
            "Accepted VK text request failed: user_id=%s peer_id=%s error=%s",
            user_id,
            peer_id,
            str(error),
        )


def run_accepted_vk_text_request(
    *,
    user_id: int,
    peer_id: int,
    text: str,
    provider: TextGenerationProvider,
    messages_api: VkMessagesApi,
    persist_exchange: Callable[..., None],
    consume_user_tokens: Callable[..., None] | None = None,
) -> None:
    if consume_user_tokens is None:
        consume_user_tokens = _consume_user_tokens

    result = provider.generate_text(text)
    persist_exchange(
        user_id=user_id,
        peer_id=peer_id,
        request_text=text,
        response_text=result.text,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
    )
    consume_user_tokens(user_id=user_id, total_tokens=result.total_tokens)
    deliver_planned_vk_reaction(
        _build_reply_event(peer_id=peer_id, text=text),
        VkOutwardReactionPlan(
            action="send_text",
            text=result.text,
            keyboard=build_dialog_menu_keyboard(),
        ),
        messages_api=messages_api,
    )
    logger.info("Accepted VK text request completed: user_id=%s peer_id=%s", user_id, peer_id)


def _build_text_provider(
    settings,
    *,
    peer_id: int,
    provider_code: str | None = None,
) -> TextGenerationProvider | None:
    selected_provider = provider_code or settings.ai_provider
    if selected_provider == "claude":
        if not settings.claude_api_key:
            logger.warning(
                "Accepted VK text request skipped: peer_id=%s reason=missing_claude_api_key",
                peer_id,
            )
            return None

        return ClaudeMessagesTextProvider(
            api_key=settings.claude_api_key,
            model=settings.claude_model,
        )

    if selected_provider == "gemini":
        if not settings.gemini_api_key:
            logger.warning(
                "Accepted VK text request skipped: peer_id=%s reason=missing_gemini_api_key",
                peer_id,
            )
            return None

        return GeminiGenerateContentProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )

    if not settings.openai_api_key:
        logger.warning(
            "Accepted VK text request skipped: peer_id=%s reason=missing_openai_api_key",
            peer_id,
        )
        return None

    return OpenAIResponsesTextProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )


def _resolve_provider_code_for_user(*, user_id: int, fallback: str) -> str:
    session_factory = get_session_factory()
    with session_factory() as session:
        user = UserService(session=session).get_by_id(user_id)
        if user is None or not user.selected_provider:
            return fallback

        return get_provider_option(user.selected_provider).code


def _persist_accepted_text_exchange(
    *,
    user_id: int,
    peer_id: int,
    request_text: str,
    response_text: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
) -> None:
    session_factory = get_session_factory()
    with session_factory() as session:
        service = AcceptedRequestPersistenceService(session=session)
        service.record_text_exchange(
            user_id=user_id,
            peer_id=peer_id,
            request_text=request_text,
            response_text=response_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )


def _consume_user_tokens(*, user_id: int, total_tokens: int) -> None:
    session_factory = get_session_factory()
    with session_factory() as session:
        service = SubscriptionService(session=session)
        service.consume_tokens_if_present(
            user_id=user_id,
            total_tokens=total_tokens,
        )


def _build_reply_event(*, peer_id: int, text: str) -> NormalizedVkEvent:
    return NormalizedVkEvent(
        event_type="message_new",
        group_id=1,
        peer_id=peer_id,
        payload={"message": {"text": text}},
    )
