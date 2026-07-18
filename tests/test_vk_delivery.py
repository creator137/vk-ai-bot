from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import parse_qs
import re

import httpx

from app.vk_transport.keyboards import build_cabinet_inline_keyboard
from app.vk_transport.delivery import deliver_planned_vk_reaction
from app.vk_transport.outward_reactions import VkOutwardReactionPlan
from app.vk_transport.schemas import NormalizedVkEvent
from app.vk_transport.vk_api import VkMessagesApi


class VkMessagesApiTests(unittest.TestCase):
    def test_set_typing_activity_calls_messages_set_activity(self) -> None:
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

        api.set_typing_activity(peer_id=2000000001)

        self.assertEqual(captured["url"], "https://api.vk.com/method/messages.setActivity")
        body = parse_qs(captured["body"])
        self.assertEqual(body["peer_id"], ["2000000001"])
        self.assertEqual(body["type"], ["typing"])
        self.assertEqual(body["access_token"], ["test-token"])
        self.assertEqual(body["v"], ["5.199"])

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

        api.send_text_message(
            peer_id=2000000001,
            text="Denied",
            keyboard=build_cabinet_inline_keyboard(),
        )

        self.assertEqual(captured["url"], "https://api.vk.com/method/messages.send")
        body = parse_qs(captured["body"])
        self.assertEqual(body["peer_id"], ["2000000001"])
        self.assertEqual(body["message"], ["Denied"])
        self.assertEqual(body["access_token"], ["test-token"])
        self.assertEqual(body["v"], ["5.199"])
        self.assertIn("keyboard", body)
        self.assertIn("random_id", body)

    def test_send_text_message_splits_long_text_into_multiple_vk_messages(self) -> None:
        requests: list[dict[str, list[str]]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) != "https://api.vk.com/method/messages.send":
                raise AssertionError(f"Unexpected request: {request.method} {request.url}")
            requests.append(parse_qs(request.content.decode()))
            return httpx.Response(200, json={"response": 1})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        api = VkMessagesApi(
            token="test-token",
            api_version="5.199",
            client=client,
        )

        long_text = ("Привет! " * 900).strip()

        api.send_text_message(
            peer_id=2000000001,
            text=long_text,
            keyboard=build_cabinet_inline_keyboard(),
        )

        self.assertGreater(len(requests), 1)
        self.assertTrue(all(len(item["message"][0]) <= 3500 for item in requests))
        self.assertTrue(
            all(
                re.match(r"^\[\d+/\d+\]\n", item["message"][0]) is not None
                for item in requests
            )
        )
        self.assertNotIn("keyboard", requests[0])
        self.assertIn("keyboard", requests[-1])
        rebuilt = " ".join(
            re.sub(r"^\[\d+/\d+\]\n", "", item["message"][0]).strip()
            for item in requests
        )
        self.assertEqual(rebuilt, long_text)

    def test_send_text_message_uploads_image_and_sets_attachment(self) -> None:
        requests: list[tuple[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append((request.method, str(request.url)))
            if str(request.url) == "https://api.vk.com/method/photos.getMessagesUploadServer":
                return httpx.Response(200, json={"response": {"upload_url": "https://upload.vk.test/messages"}})
            if str(request.url) == "https://upload.vk.test/messages":
                return httpx.Response(200, json={"server": 11, "photo": '[{"id":1}]', "hash": "abc"})
            if str(request.url) == "https://api.vk.com/method/photos.saveMessagesPhoto":
                return httpx.Response(200, json={"response": [{"owner_id": -10, "id": 55, "access_key": "key"}]})
            if str(request.url) == "https://api.vk.com/method/messages.send":
                body = parse_qs(request.content.decode())
                self.assertEqual(body["attachment"], ["photo-10_55_key"])
                return httpx.Response(200, json={"response": 1})
            raise AssertionError(f"Unexpected request: {request.method} {request.url}")

        client = httpx.Client(transport=httpx.MockTransport(handler))
        api = VkMessagesApi(
            token="test-token",
            api_version="5.199",
            client=client,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "plan.jpeg"
            image_path.write_bytes(b"fake-image")
            api.send_text_message(
                peer_id=2000000001,
                text="Plan",
                image_path=str(image_path),
            )

        self.assertEqual(
            [url for _, url in requests],
            [
                "https://api.vk.com/method/photos.getMessagesUploadServer",
                "https://upload.vk.test/messages",
                "https://api.vk.com/method/photos.saveMessagesPhoto",
                "https://api.vk.com/method/messages.send",
            ],
        )


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
            keyboard=None,
            image_path=None,
        )

    def test_send_text_reaction_with_image_calls_adapter(self) -> None:
        messages_api = Mock()

        deliver_planned_vk_reaction(
            _build_event(),
            VkOutwardReactionPlan(
                action="send_text",
                text="Plan",
                image_path="/tmp/plan.jpeg",
            ),
            messages_api=messages_api,
        )

        messages_api.send_text_message.assert_called_once_with(
            peer_id=321,
            text="Plan",
            keyboard=None,
            image_path="/tmp/plan.jpeg",
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
