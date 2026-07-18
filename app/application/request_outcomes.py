from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class RequestOutcome:
    status: Literal["skipped", "denied", "accepted", "handled"]
    reason: Literal[
        "missing_actor_id",
        "access_denied",
        "subscription_missing",
        "subscription_exhausted",
        "access_allowed",
        "provider_selected",
        "provider_unavailable",
        "cabinet_shown",
        "instruction_shown",
        "support_shown",
        "plans_shown",
        "plan_preview_shown",
    ]
    user_id: int | None = None
