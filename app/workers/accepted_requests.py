from __future__ import annotations

import logging
import mimetypes
from collections.abc import Callable

import dramatiq
import httpx

from app.ai.provider import (
    ClaudeMessagesTextProvider,
    ClaudeProviderError,
    GeminiGenerateContentProvider,
    GeminiProviderError,
    ImageInput,
    OpenAIProviderError,
    OpenAIResponsesTextProvider,
    TextGenerationProvider,
    VisionGenerationProvider,
)
from app.ai.provider_catalog import get_provider_option
from app.core.config import get_settings
from app.db.session import get_session_factory
from app.requests.service import AcceptedDialogueTurn, AcceptedRequestPersistenceService
from app.subscriptions.service import SubscriptionService
from app.users.service import UserService
from app.vk_transport.delivery import deliver_planned_vk_reaction
from app.vk_transport.keyboards import build_dialog_menu_keyboard
from app.vk_transport.outward_reactions import VkOutwardReactionPlan
from app.vk_transport.schemas import NormalizedVkEvent
from app.vk_transport.vk_api import VkApiError, VkMessagesApi

logger = logging.getLogger(__name__)
MAX_CONTEXT_TURNS = 6
DEFAULT_IMAGE_PROMPT = (
    "Пользователь прислал изображение. Опиши, что на нем видно, "
    "и помоги по содержимому фото."
)


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


@dramatiq.actor(queue_name="accepted_requests")
def process_vk_accepted_photo_request(
    user_id: int,
    peer_id: int,
    text: str | None,
    image_urls: list[str],
) -> None:
    settings = get_settings()
    if not settings.vk_outbound_token:
        logger.warning(
            "Accepted VK photo request skipped: peer_id=%s reason=missing_vk_outbound_token",
            peer_id,
        )
        return

    provider_code = _resolve_provider_code_for_user(user_id=user_id, fallback=settings.ai_provider)
    provider = _build_vision_provider(
        settings,
        peer_id=peer_id,
        provider_code=provider_code,
    )
    if provider is None:
        return

    messages_api = VkMessagesApi(
        token=settings.vk_outbound_token,
        api_version=settings.vk_api_version,
    )
    try:
        run_accepted_vk_photo_request(
            user_id=user_id,
            peer_id=peer_id,
            text=text,
            image_urls=image_urls,
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
            "Accepted VK photo request failed: user_id=%s peer_id=%s error=%s",
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
    load_dialogue_context: Callable[..., list[AcceptedDialogueTurn]] | None = None,
) -> None:
    if consume_user_tokens is None:
        consume_user_tokens = _consume_user_tokens
    if load_dialogue_context is None:
        load_dialogue_context = _load_dialogue_context

    context_turns = load_dialogue_context(
        user_id=user_id,
        peer_id=peer_id,
        limit=MAX_CONTEXT_TURNS,
    )
    prompt = _build_contextual_prompt(
        current_text=text,
        context_turns=context_turns,
    )
    result = provider.generate_text(prompt)
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


def run_accepted_vk_photo_request(
    *,
    user_id: int,
    peer_id: int,
    text: str | None,
    image_urls: list[str],
    provider: VisionGenerationProvider,
    messages_api: VkMessagesApi,
    persist_exchange: Callable[..., None],
    consume_user_tokens: Callable[..., None] | None = None,
    load_dialogue_context: Callable[..., list[AcceptedDialogueTurn]] | None = None,
    prepare_images: Callable[..., list[ImageInput]] | None = None,
) -> None:
    if consume_user_tokens is None:
        consume_user_tokens = _consume_user_tokens
    if load_dialogue_context is None:
        load_dialogue_context = _load_dialogue_context
    if prepare_images is None:
        prepare_images = _prepare_images_for_provider

    normalized_text = _normalize_request_text(text)
    context_turns = load_dialogue_context(
        user_id=user_id,
        peer_id=peer_id,
        limit=MAX_CONTEXT_TURNS,
    )
    prompt = _build_contextual_prompt(
        current_text=normalized_text or DEFAULT_IMAGE_PROMPT,
        context_turns=context_turns,
    )
    if normalized_text is None:
        prompt = (
            f"{prompt}\n\n"
            "В текущем сообщении нет текста, только изображение. "
            "Сконцентрируйся на анализе фото и дай полезный ответ пользователю."
        )

    result = provider.generate_text_from_images(
        prompt=prompt,
        images=prepare_images(provider=provider, image_urls=image_urls),
    )
    persist_exchange(
        user_id=user_id,
        peer_id=peer_id,
        request_text=_build_photo_request_text(normalized_text, image_count=len(image_urls)),
        response_text=result.text,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
    )
    consume_user_tokens(user_id=user_id, total_tokens=result.total_tokens)
    deliver_planned_vk_reaction(
        _build_reply_event(peer_id=peer_id, text=normalized_text or "[photo]"),
        VkOutwardReactionPlan(
            action="send_text",
            text=result.text,
            keyboard=build_dialog_menu_keyboard(),
        ),
        messages_api=messages_api,
    )
    logger.info("Accepted VK photo request completed: user_id=%s peer_id=%s", user_id, peer_id)


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
            max_tokens=settings.claude_max_tokens,
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


def _build_vision_provider(
    settings,
    *,
    peer_id: int,
    provider_code: str | None = None,
) -> VisionGenerationProvider | None:
    selected_provider = provider_code or settings.ai_provider
    if selected_provider == "claude":
        if not settings.claude_api_key:
            logger.warning(
                "Accepted VK photo request skipped: peer_id=%s reason=missing_claude_api_key",
                peer_id,
            )
            return None

        return ClaudeMessagesTextProvider(
            api_key=settings.claude_api_key,
            model=settings.claude_model,
            max_tokens=settings.claude_max_tokens,
        )

    if selected_provider == "gemini":
        if not settings.gemini_api_key:
            logger.warning(
                "Accepted VK photo request skipped: peer_id=%s reason=missing_gemini_api_key",
                peer_id,
            )
            return None

        return GeminiGenerateContentProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )

    if not settings.openai_api_key:
        logger.warning(
            "Accepted VK photo request skipped: peer_id=%s reason=missing_openai_api_key",
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


def _load_dialogue_context(
    *,
    user_id: int,
    peer_id: int,
    limit: int,
) -> list[AcceptedDialogueTurn]:
    session_factory = get_session_factory()
    with session_factory() as session:
        service = AcceptedRequestPersistenceService(session=session)
        return service.list_recent_dialogue_turns(
            user_id=user_id,
            peer_id=peer_id,
            limit=limit,
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


def _build_contextual_prompt(
    *,
    current_text: str,
    context_turns: list[AcceptedDialogueTurn],
) -> str:
    if not context_turns:
        return current_text

    lines = [
        "Продолжай диалог, учитывая предыдущие сообщения.",
        "Краткая история переписки:",
    ]
    for turn in context_turns:
        lines.append(f"Пользователь: {turn.request_text}")
        lines.append(f"Бот: {turn.response_text}")

    lines.extend(
        [
            "",
            "Новое сообщение пользователя:",
            current_text,
        ]
    )
    return "\n".join(lines)


def _normalize_request_text(text: str | None) -> str | None:
    if not isinstance(text, str):
        return None

    stripped = text.strip()
    if not stripped:
        return None

    return stripped


def _build_photo_request_text(text: str | None, *, image_count: int) -> str:
    if text:
        return f"[photo x{image_count}] {text}"
    return f"[photo x{image_count}]"


def _prepare_images_for_provider(
    *,
    provider: VisionGenerationProvider,
    image_urls: list[str],
) -> list[ImageInput]:
    if isinstance(provider, OpenAIResponsesTextProvider):
        return [ImageInput(image_url=url) for url in image_urls]

    return [_download_image(url) for url in image_urls]


def _download_image(url: str) -> ImageInput:
    with httpx.Client() as client:
        response = client.get(url, timeout=30.0, follow_redirects=True)
        response.raise_for_status()

    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if not content_type:
        guessed_type, _ = mimetypes.guess_type(url)
        content_type = guessed_type or "image/jpeg"

    return ImageInput(
        data=response.content,
        mime_type=content_type,
    )
