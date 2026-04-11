from __future__ import annotations

import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs

import httpx

from app.vk_transport.delivery import deliver_planned_vk_reaction
from app.vk_transport.outward_reactions import VkOutwardReactionPlan
from app.vk_transport.schemas import NormalizedVkEvent
from app.vk_transport.vk_api import VkMessagesApi


class VkMessagesApiTests(unittest.TestCase):
    def test_send_text_message_calls_messages_send(self) -> None:
        captured: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["body"] = request.content.decode()
            return httpx.Response(200, json={"response": 1})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        api = VkMessagesApi(
            token="test-token",
            api_version="5.199",
            client=client,
        )

        api.send_text_message(peer_id=2000000001, text="Denied")

        self.assertEqual(captured["url"], "https://api.vk.com/method/messages.send")
        body = parse_qs(captured["body"])
        self.assertEqual(body["peer_id"], ["2000000001"])
        self.assertEqual(body["message"], ["Denied"])
        self.assertEqual(body["access_token"], ["test-token"])
        self.assertEqual(body["v"], ["5.199"])
        self.assertIn("random_id", body)


class VkDeliveryTests(unittest.TestCase):
    def test_none_reaction_does_not_call_adapter(self) -> None:
        messages_api = Mock()

        deliver_planned_vk_reaction(
            _build_event(),
            VkOutwardReactionPlan(action="none"),
            messages_api=messages_api,
        )

        messages_api.send_text_message.assert_not_called()

    def test_send_text_reaction_calls_adapter(self) -> None:
        messages_api = Mock()

        deliver_planned_vk_reaction(
            _build_event(),
            VkOutwardReactionPlan(action="send_text", text="Denied"),
            messages_api=messages_api,
        )

        messages_api.send_text_message.assert_called_once_with(
            peer_id=321,
            text="Denied",
        )

    def test_send_text_reaction_without_peer_id_skips_delivery(self) -> None:
        messages_api = Mock()
        event = _build_event(peer_id=None)

        with patch("app.vk_transport.delivery.logger.warning") as logger_warning:
            deliver_planned_vk_reaction(
                event,
                VkOutwardReactionPlan(action="send_text", text="Denied"),
                messages_api=messages_api,
            )

        messages_api.send_text_message.assert_not_called()
        self.assertTrue(
            any(
                "VK outward reaction delivery skipped" in call.args[0]
                for call in logger_warning.call_args_list
            )
        )


def _build_event(peer_id: int | None = 321) -> NormalizedVkEvent:
    return NormalizedVkEvent(
        event_type="message_new",
        group_id=1,
        event_id="evt-1",
        actor_id=123456,
        peer_id=peer_id,
        occurred_at=1710000000,
        payload={"message": {"text": "hello"}},
    )
