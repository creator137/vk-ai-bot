from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Literal

from app.subscriptions.catalog import render_subscription_plans_text
from app.vk_transport.outcome_consumer import OutcomeConsumption
from app.vk_transport.keyboards import (
    build_cabinet_inline_keyboard,
    build_plan_detail_inline_keyboard,
    build_plans_inline_keyboard,
)

ACCESS_NOT_ACTIVE_TEXT = render_subscription_plans_text()
EXHAUSTED_BALANCE_TEXT = "\n".join(
    [
        "🔹 Баланс: 0 токенов",
        "Токены закончились, поэтому ответ сейчас не может быть сгенерирован.",
        "",
        render_subscription_plans_text(),
    ]
)


@dataclass(frozen=True, slots=True)
class VkOutwardReactionPlan:
    action: Literal["none", "send_text"]
    text: str | None = None
    keyboard: dict[str, Any] | None = None
    image_path: str | None = None


def plan_vk_outward_reaction(
    consumption: OutcomeConsumption,
    *,
    outcome_reason: str | None = None,
    handled_text: str | None = None,
    handled_view: str | None = None,
    handled_payment_url: str | None = None,
    handled_image_path: str | None = None,
) -> VkOutwardReactionPlan:
    if consumption.state == "halted":
        text = ACCESS_NOT_ACTIVE_TEXT
        if outcome_reason == "subscription_exhausted":
            text = EXHAUSTED_BALANCE_TEXT
        return VkOutwardReactionPlan(
            action="send_text",
            text=text,
            keyboard=build_plans_inline_keyboard(),
        )

    if consumption.state == "completed" and handled_text:
        if handled_view == "plans":
            keyboard = build_plans_inline_keyboard()
        elif handled_view == "plan_detail":
            keyboard = build_plan_detail_inline_keyboard(handled_payment_url)
        else:
            keyboard = build_cabinet_inline_keyboard()
        return VkOutwardReactionPlan(
            action="send_text",
            text=handled_text,
            keyboard=keyboard,
            image_path=handled_image_path,
        )

    return VkOutwardReactionPlan(action="none")
