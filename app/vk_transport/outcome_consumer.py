from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.application.request_outcomes import RequestOutcome


@dataclass(frozen=True, slots=True)
class OutcomeConsumption:
    state: Literal["ignored", "halted", "ready_for_next_stage", "completed"]


def consume_request_outcome(outcome: RequestOutcome) -> OutcomeConsumption:
    if outcome.status == "skipped":
        return OutcomeConsumption(state="ignored")

    if outcome.status == "denied":
        return OutcomeConsumption(state="halted")

    if outcome.status == "handled":
        return OutcomeConsumption(state="completed")

    return OutcomeConsumption(state="ready_for_next_stage")
