from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.core.config import Settings
from app.vk_transport.schemas import NormalizedVkEvent
from app.vk_transport.service import get_vk_event_handoff


class RecordingVkEventHandoff:
    def __init__(self) -> None:
        self.events: list[NormalizedVkEvent] = []

    def handle(self, event: NormalizedVkEvent) -> None:
        self.events.append(event)


class VkCallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.handoff = RecordingVkEventHandoff()
        app.dependency_overrides[get_vk_event_handoff] = lambda: self.handoff

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_vk_callback_returns_ok_and_hands_off_normalized_event(self) -> None:
        payload = {
            "type": "message_new",
            "group_id": 100,
            "event_id": "evt-1",
            "object": {
                "message": {
                    "from_id": 42,
                    "peer_id": 77,
                    "date": 1710000000,
                    "text": "hello",
                }
            },
        }

        with patch(
            "app.api.routes.vk.get_settings",
            return_value=Settings(),
        ):
            with TestClient(app) as client:
                response = client.post("/webhooks/vk", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "ok")
        self.assertEqual(len(self.handoff.events), 1)

        event = self.handoff.events[0]
        self.assertEqual(event.source, "vk")
        self.assertEqual(event.event_type, "message_new")
        self.assertEqual(event.group_id, 100)
        self.assertEqual(event.event_id, "evt-1")
        self.assertEqual(event.actor_id, 42)
        self.assertEqual(event.peer_id, 77)
        self.assertEqual(event.occurred_at, 1710000000)

    def test_vk_callback_rejects_invalid_payload(self) -> None:
        with patch(
            "app.api.routes.vk.get_settings",
            return_value=Settings(),
        ):
            with TestClient(app) as client:
                response = client.post("/webhooks/vk", json={"group_id": 100, "object": {}})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(len(self.handoff.events), 0)

    def test_vk_callback_rejects_invalid_secret(self) -> None:
        payload = {
            "type": "message_new",
            "group_id": 100,
            "secret": "wrong-secret",
            "object": {},
        }

        with patch(
            "app.api.routes.vk.get_settings",
            return_value=Settings(vk_callback_secret="expected-secret"),
        ):
            with TestClient(app) as client:
                response = client.post("/webhooks/vk", json=payload)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Invalid VK callback secret")
        self.assertEqual(len(self.handoff.events), 0)

    def test_vk_confirmation_returns_configured_token(self) -> None:
        payload = {
            "type": "confirmation",
            "group_id": 100,
            "object": {},
        }

        with patch(
            "app.api.routes.vk.get_settings",
            return_value=Settings(vk_callback_confirmation_token="confirmation-code"),
        ):
            with TestClient(app) as client:
                response = client.post("/webhooks/vk", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "confirmation-code")
        self.assertEqual(len(self.handoff.events), 0)


if __name__ == "__main__":
    unittest.main()
