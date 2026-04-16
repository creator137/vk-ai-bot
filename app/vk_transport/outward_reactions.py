from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Literal

from app.subscriptions.catalog import render_subscription_plans_text
from app.vk_transport.outcome_consumer import OutcomeConsumption
from app.vk_transport.keyboards import (
    build_cabinet_inline_keyboard,
    build_plans_inline_keyboard,
)

ACCESS_NOT_ACTIVE_TEXT = render_subscription_plans_text()


@dataclass(frozen=True, slots=True)
class VkOutwardReactionPlan:
    action: Literal["none", "send_text"]
    text: str | None = None
    keyboard: dict[str, Any] | None = None


def plan_vk_outward_reaction(
    consumption: OutcomeConsumption,
    *,
    handled_text: str | None = None,
    handled_view: str | None = None,
) -> VkOutwardReactionPlan:
    if consumption.state == "halted":
        return VkOutwardReactionPlan(
            action="send_text",
            text=ACCESS_NOT_ACTIVE_TEXT,
            keyboard=build_plans_inline_keyboard(),
        )

    if consumption.state == "completed" and handled_text:
        keyboard = (
            build_plans_inline_keyboard()
            if handled_view == "plans"
            else build_cabinet_inline_keyboard()
        )
        return VkOutwardReactionPlan(
            action="send_text",
            text=handled_text,
            keyboard=keyboard,
        )

    return VkOutwardReactionPlan(action="none")
