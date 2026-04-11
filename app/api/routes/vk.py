from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.vk_transport.service import (
    VkEventHandoff,
    ensure_vk_callback_secret,
    get_vk_event_handoff,
    normalize_vk_event,
)
from app.vk_transport.schemas import VkCallbackPayload

router = APIRouter(prefix="/webhooks/vk", tags=["vk"])


@router.post("", response_class=PlainTextResponse)
def vk_callback(
    payload: VkCallbackPayload,
    handoff: VkEventHandoff = Depends(get_vk_event_handoff),
) -> PlainTextResponse:
    settings = get_settings()
    if payload.type == "confirmation":
        if not settings.vk_callback_confirmation_token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="VK confirmation token is not configured",
            )
        return PlainTextResponse(settings.vk_callback_confirmation_token)

    ensure_vk_callback_secret(
        payload_secret=payload.secret,
        expected_secret=settings.vk_callback_secret,
    )

    normalized_event = normalize_vk_event(payload)
    handoff.handle(normalized_event)
    return PlainTextResponse("ok")

