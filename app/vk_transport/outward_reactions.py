from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.vk_transport.outcome_consumer import OutcomeConsumption

ACCESS_NOT_ACTIVE_TEXT = "Доступ к обработке запросов пока не активирован."


@dataclass(frozen=True, slots=True)
class VkOutwardReactionPlan:
    action: Literal["none", "send_text"]
    text: str | None = None


def plan_vk_outward_reaction(consumption: OutcomeConsumption) -> VkOutwardReactionPlan:
    if consumption.state == "halted":
        return VkOutwardReactionPlan(
            action="send_text",
            text=ACCESS_NOT_ACTIVE_TEXT,
        )

    return VkOutwardReactionPlan(action="none")
