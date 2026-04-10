from __future__ import annotations

import unittest
from unittest.mock import patch

from app.application.request_outcomes import RequestOutcome
from app.vk_transport.schemas import NormalizedVkEvent
from app.vk_transport.service import ApplicationVkEventHandoff


class _SessionScope:
    def __enter__(self) -> object:
        return object()

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class VkConsumedOutcomeHandlingTests(unittest.TestCase):
    def test_ignored_branch_is_handled_explicitly(self) -> None:
        event = _build_event()
        outcome = RequestOutcome(status="skipped", reason="missing_actor_id")

        with patch(
            "app.vk_transport.service.get_session_factory",
            return_value=lambda: _SessionScope(),
        ), patch(
            "app.vk_transport.service._dispatch_to_application",
            return_value=outcome,
        ), patch("app.vk_transport.service.logger.info") as logger_info:
            returned = ApplicationVkEventHandoff().handle(event)

        self.assertEqual(returned, outcome)
        self.assertTrue(
            any("VK event branch ignored" in call.args[0] for call in logger_info.call_args_list)
        )

    def test_halted_branch_is_handled_explicitly(self) -> None:
        event = _build_event()
        outcome = RequestOutcome(
            status="denied",
            reason="access_denied",
            user_id=1,
        )

        with patch(
            "app.vk_transport.service.get_session_factory",
            return_value=lambda: _SessionScope(),
        ), patch(
            "app.vk_transport.service._dispatch_to_application",
            return_value=outcome,
        ), patch("app.vk_transport.service.logger.info") as logger_info:
            returned = ApplicationVkEventHandoff().handle(event)

        self.assertEqual(returned, outcome)
        self.assertTrue(
            any("VK event branch halted" in call.args[0] for call in logger_info.call_args_list)
        )

    def test_ready_for_next_stage_branch_is_handled_explicitly(self) -> None:
        event = _build_event()
        outcome = RequestOutcome(
            status="accepted",
            reason="access_allowed",
            user_id=1,
        )

        with patch(
            "app.vk_transport.service.get_session_factory",
            return_value=lambda: _SessionScope(),
        ), patch(
            "app.vk_transport.service._dispatch_to_application",
            return_value=outcome,
        ), patch("app.vk_transport.service.logger.info") as logger_info:
            returned = ApplicationVkEventHandoff().handle(event)

        self.assertEqual(returned, outcome)
        self.assertTrue(
            any(
                "VK event branch ready for next stage" in call.args[0]
                for call in logger_info.call_args_list
            )
        )


def _build_event() -> NormalizedVkEvent:
    return NormalizedVkEvent(
        event_type="message_new",
        group_id=1,
        event_id="evt-1",
        actor_id=123456,
        peer_id=321,
        occurred_at=1710000000,
        payload={"message": {"text": "hello"}},
    )
