from __future__ import annotations

import unittest
from unittest.mock import Mock

from app.ai.provider import TextGenerationResult
from app.vk_transport.keyboards import build_dialog_menu_keyboard
from app.workers.accepted_requests import (
    DEFAULT_IMAGE_PROMPT,
    run_accepted_vk_photo_request,
    run_accepted_vk_text_request,
)


class AcceptedWorkerTests(unittest.TestCase):
    def test_worker_calls_provider_persists_exchange_spends_tokens_and_sends_vk_text_reply(self) -> None:
        provider = Mock()
        provider.generate_text.return_value = TextGenerationResult(
            text="AI reply",
            input_tokens=13,
            output_tokens=5,
        )
        messages_api = Mock()
        persist_exchange = Mock()
        consume_user_tokens = Mock()
        load_dialogue_context = Mock(return_value=[])

        run_accepted_vk_text_request(
            user_id=11,
            peer_id=321,
            text="hello",
            provider=provider,
            messages_api=messages_api,
            persist_exchange=persist_exchange,
            consume_user_tokens=consume_user_tokens,
            load_dialogue_context=load_dialogue_context,
        )

        load_dialogue_context.assert_called_once_with(
            user_id=11,
            peer_id=321,
            limit=6,
        )
        provider.generate_text.assert_called_once_with("hello")
        persist_exchange.assert_called_once_with(
            user_id=11,
            peer_id=321,
            request_text="hello",
            response_text="AI reply",
            input_tokens=13,
            output_tokens=5,
            total_tokens=18,
        )
        consume_user_tokens.assert_called_once_with(
            user_id=11,
            total_tokens=18,
        )
        messages_api.send_text_message.assert_called_once_with(
            peer_id=321,
            text="AI reply",
            keyboard=build_dialog_menu_keyboard(),
            image_path=None,
        )

    def test_worker_sends_recent_dialogue_history_to_provider(self) -> None:
        provider = Mock()
        provider.generate_text.return_value = TextGenerationResult(
            text="AI reply",
            input_tokens=8,
            output_tokens=4,
        )
        messages_api = Mock()
        persist_exchange = Mock()
        load_dialogue_context = Mock(
            return_value=[
                Mock(request_text="Hi", response_text="Hi!"),
                Mock(request_text="How are you?", response_text="Doing well."),
            ]
        )
        consume_user_tokens = Mock()

        run_accepted_vk_text_request(
            user_id=11,
            peer_id=321,
            text="Remember that my name is Anton",
            provider=provider,
            messages_api=messages_api,
            persist_exchange=persist_exchange,
            consume_user_tokens=consume_user_tokens,
            load_dialogue_context=load_dialogue_context,
        )

        sent_prompt = provider.generate_text.call_args.args[0]
        self.assertIn("Hi", sent_prompt)
        self.assertIn("Hi!", sent_prompt)
        self.assertIn("Remember that my name is Anton", sent_prompt)

    def test_photo_worker_calls_vision_provider_and_sends_vk_reply(self) -> None:
        provider = Mock()
        provider.generate_text_from_images.return_value = TextGenerationResult(
            text="There is a cat on the couch.",
            input_tokens=21,
            output_tokens=9,
        )
        messages_api = Mock()
        persist_exchange = Mock()
        consume_user_tokens = Mock()
        load_dialogue_context = Mock(return_value=[])

        run_accepted_vk_photo_request(
            user_id=11,
            peer_id=321,
            text=None,
            image_urls=["https://example.com/cat.jpg"],
            provider=provider,
            messages_api=messages_api,
            persist_exchange=persist_exchange,
            consume_user_tokens=consume_user_tokens,
            load_dialogue_context=load_dialogue_context,
            prepare_images=lambda **_: [],
        )

        provider.generate_text_from_images.assert_called_once()
        call = provider.generate_text_from_images.call_args
        self.assertIn(DEFAULT_IMAGE_PROMPT, call.kwargs["prompt"])
        self.assertEqual(call.kwargs["images"], [])
        persist_exchange.assert_called_once_with(
            user_id=11,
            peer_id=321,
            request_text="[photo x1]",
            response_text="There is a cat on the couch.",
            input_tokens=21,
            output_tokens=9,
            total_tokens=30,
        )
        consume_user_tokens.assert_called_once_with(
            user_id=11,
            total_tokens=30,
        )
        messages_api.send_text_message.assert_called_once_with(
            peer_id=321,
            text="There is a cat on the couch.",
            keyboard=build_dialog_menu_keyboard(),
            image_path=None,
        )
