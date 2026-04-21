from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from app.application.accepted_dispatch import dispatch_accepted_vk_event
from app.vk_transport.schemas import NormalizedVkEvent


class AcceptedDispatchTests(unittest.TestCase):
    def test_accepted_text_message_dispatches_worker_task(self) -> None:
        event = _build_event(
            event_type="message_new",
            payload={"message": {"text": "hello"}},
        )
        actor = Mock()

        with patch(
            "app.application.accepted_dispatch._get_accepted_request_actor",
            return_value=actor,
        ):
            dispatch_accepted_vk_event(event)

        actor.send.assert_called_once_with(1, 321, "hello")

    def test_photo_message_dispatches_photo_worker_task(self) -> None:
        event = _build_event(
            event_type="message_new",
            payload={
                "message": {
                    "text": "",
                    "attachments": [
                        {
                            "type": "photo",
                            "photo": {
                                "sizes": [
                                    {"url": "https://example.com/small.jpg", "width": 100, "height": 50},
                                    {"url": "https://example.com/large.jpg", "width": 1200, "height": 900},
                                ]
                            },
                        }
                    ],
                }
            },
        )
        actor = Mock()

        with patch(
            "app.application.accepted_dispatch._get_accepted_photo_request_actor",
            return_value=actor,
        ):
            dispatch_accepted_vk_event(event)

        actor.send.assert_called_once_with(1, 321, None, ["https://example.com/large.jpg"])

    def test_accepted_non_text_or_non_message_event_does_not_dispatch(self) -> None:
        cases = [
            _build_event(
                event_type="message_new",
                payload={"message": {"text": "", "attachments": []}},
            ),
            _build_event(
                event_type="message_allow",
                payload={},
            ),
        ]

        for event in cases:
            with self.subTest(event_type=event.event_type):
                actor = Mock()
                photo_actor = Mock()
                with patch(
                    "app.application.accepted_dispatch._get_accepted_request_actor",
                    return_value=actor,
                ), patch(
                    "app.application.accepted_dispatch._get_accepted_photo_request_actor",
                    return_value=photo_actor,
                ):
                    dispatch_accepted_vk_event(event)

                actor.send.assert_not_called()
                photo_actor.send.assert_not_called()


def _build_event(
    *,
    event_type: str,
    payload: dict[str, object],
    peer_id: int | None = 321,
) -> NormalizedVkEvent:
    return NormalizedVkEvent(
        event_type=event_type,
        group_id=1,
        event_id="evt-1",
        actor_id=123456,
        peer_id=peer_id,
        occurred_at=1710000000,
        payload={"user_id": 1, **payload},
    )
