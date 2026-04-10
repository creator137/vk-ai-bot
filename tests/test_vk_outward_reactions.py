from __future__ import annotations

import unittest

from app.vk_transport.outcome_consumer import OutcomeConsumption
from app.vk_transport.outward_reactions import (
    ACCESS_NOT_ACTIVE_TEXT,
    plan_vk_outward_reaction,
)


class VkOutwardReactionsTests(unittest.TestCase):
    def test_ignored_branch_has_no_outward_reaction(self) -> None:
        reaction = plan_vk_outward_reaction(OutcomeConsumption(state="ignored"))

        self.assertEqual(reaction.action, "none")
        self.assertIsNone(reaction.text)

    def test_halted_branch_plans_denied_text_reaction(self) -> None:
        reaction = plan_vk_outward_reaction(OutcomeConsumption(state="halted"))

        self.assertEqual(reaction.action, "send_text")
        self.assertEqual(reaction.text, ACCESS_NOT_ACTIVE_TEXT)

    def test_ready_for_next_stage_branch_has_no_outward_reaction(self) -> None:
        reaction = plan_vk_outward_reaction(OutcomeConsumption(state="ready_for_next_stage"))

        self.assertEqual(reaction.action, "none")
        self.assertIsNone(reaction.text)
