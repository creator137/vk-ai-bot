from __future__ import annotations

import unittest
from unittest.mock import Mock

from app.workers.accepted_requests import run_accepted_vk_text_request


class AcceptedWorkerTests(unittest.TestCase):
    def test_worker_calls_provider_persists_exchange_and_sends_vk_text_reply(self) -> None:
        provider = Mock()
        provider.generate_text.return_value = "AI reply"
        messages_api = Mock()
        persist_exchange = Mock()

        run_accepted_vk_text_request(
            user_id=11,
            peer_id=321,
            text="hello",
            provider=provider,
            messages_api=messages_api,
            persist_exchange=persist_exchange,
        )

        provider.generate_text.assert_called_once_with("hello")
        persist_exchange.assert_called_once_with(
            user_id=11,
            peer_id=321,
            request_text="hello",
            response_text="AI reply",
        )
        messages_api.send_text_message.assert_called_once_with(
            peer_id=321,
            text="AI reply",
        )
