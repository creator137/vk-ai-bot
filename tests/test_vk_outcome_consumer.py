from __future__ import annotations

import unittest

from app.application.request_outcomes import RequestOutcome
from app.vk_transport.outcome_consumer import consume_request_outcome


class VkOutcomeConsumerTests(unittest.TestCase):
    def test_skipped_outcome_maps_to_ignored(self) -> None:
        outcome = RequestOutcome(status="skipped", reason="missing_actor_id")

        consumed = consume_request_outcome(outcome)

        self.assertEqual(consumed.state, "ignored")

    def test_denied_outcome_maps_to_halted(self) -> None:
        outcome = RequestOutcome(
            status="denied",
            reason="access_denied",
            user_id=1,
        )

        consumed = consume_request_outcome(outcome)

        self.assertEqual(consumed.state, "halted")

    def test_accepted_outcome_maps_to_ready_for_next_stage(self) -> None:
        outcome = RequestOutcome(
            status="accepted",
            reason="access_allowed",
            user_id=1,
        )

        consumed = consume_request_outcome(outcome)

        self.assertEqual(consumed.state, "ready_for_next_stage")
