from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class RequestOutcome:
    status: Literal["skipped", "denied", "accepted"]
    reason: Literal["missing_actor_id", "access_denied", "access_allowed"]
    user_id: int | None = None
