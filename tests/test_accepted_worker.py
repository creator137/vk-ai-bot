from __future__ import annotations

import time
import unittest
from unittest.mock import Mock, call, patch

import httpx

from app.ai.provider import TextGenerationResult
from app.vk_transport.keyboards import build_dialog_menu_keyboard
from app.workers.accepted_requests import (
    DEFAULT_IMAGE_PROMPT,
    TIMEOUT_FALLBACK_TEXT,
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
        messages_api.set_typing_activity.assert_called_once_with(peer_id=321)
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
        self.assertLess(
            messages_api.method_calls.index(call.set_typing_activity(peer_id=321)),
            messages_api.method_calls.index(
                call.send_text_message(
                    peer_id=321,
                    text="AI reply",
                    keyboard=build_dialog_menu_keyboard(),
                    image_path=None,
                )
            ),
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
        messages_api.set_typing_activity.assert_called_once_with(peer_id=321)
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
        self.assertLess(
            messages_api.method_calls.index(call.set_typing_activity(peer_id=321)),
            messages_api.method_calls.index(
                call.send_text_message(
                    peer_id=321,
                    text="There is a cat on the couch.",
                    keyboard=build_dialog_menu_keyboard(),
                    image_path=None,
                )
            ),
        )
        messages_api.send_text_message.assert_called_once_with(
            peer_id=321,
            text="There is a cat on the couch.",
            keyboard=build_dialog_menu_keyboard(),
            image_path=None,
        )

    def test_worker_retries_text_request_once_after_timeout(self) -> None:
        provider = Mock()
        provider.generate_text.side_effect = [
            httpx.ReadTimeout("timeout"),
            TextGenerationResult(text="AI reply", input_tokens=3, output_tokens=2),
        ]
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

        self.assertEqual(provider.generate_text.call_count, 2)
        messages_api.set_typing_activity.assert_called()
        messages_api.send_text_message.assert_called_once_with(
            peer_id=321,
            text="AI reply",
            keyboard=build_dialog_menu_keyboard(),
            image_path=None,
        )

    def test_worker_switches_to_fallback_provider_after_timeout(self) -> None:
        primary_provider = Mock()
        primary_provider.generate_text.side_effect = [
            httpx.ReadTimeout("timeout"),
            httpx.ReadTimeout("timeout"),
        ]
        fallback_provider = Mock()
        fallback_provider.generate_text.return_value = TextGenerationResult(
            text="Fallback reply",
            input_tokens=4,
            output_tokens=3,
        )
        messages_api = Mock()
        persist_exchange = Mock()
        consume_user_tokens = Mock()
        load_dialogue_context = Mock(return_value=[])

        run_accepted_vk_text_request(
            user_id=11,
            peer_id=321,
            text="hello",
            provider=primary_provider,
            provider_code="claude",
            timeout_fallback_providers=[("openai", fallback_provider)],
            messages_api=messages_api,
            persist_exchange=persist_exchange,
            consume_user_tokens=consume_user_tokens,
            load_dialogue_context=load_dialogue_context,
        )

        self.assertEqual(primary_provider.generate_text.call_count, 2)
        fallback_provider.generate_text.assert_called_once_with("hello")
        messages_api.send_text_message.assert_called_once_with(
            peer_id=321,
            text="Fallback reply",
            keyboard=build_dialog_menu_keyboard(),
            image_path=None,
        )

    def test_worker_sends_fallback_after_repeated_timeout(self) -> None:
        provider = Mock()
        provider.generate_text.side_effect = httpx.ReadTimeout("timeout")
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

        self.assertEqual(provider.generate_text.call_count, 2)
        messages_api.set_typing_activity.assert_called()
        persist_exchange.assert_not_called()
        consume_user_tokens.assert_not_called()
        messages_api.send_text_message.assert_called_once_with(
            peer_id=321,
            text=TIMEOUT_FALLBACK_TEXT,
            keyboard=build_dialog_menu_keyboard(),
            image_path=None,
        )

    def test_worker_refreshes_typing_indicator_while_provider_is_slow(self) -> None:
        provider = Mock()

        def slow_generate_text(_: str) -> TextGenerationResult:
            time.sleep(0.03)
            return TextGenerationResult(text="AI reply", input_tokens=1, output_tokens=1)

        provider.generate_text.side_effect = slow_generate_text
        messages_api = Mock()

        with patch("app.workers.accepted_requests.TYPING_ACTIVITY_REFRESH_SECONDS", 0.01):
            run_accepted_vk_text_request(
                user_id=11,
                peer_id=321,
                text="hello",
                provider=provider,
                messages_api=messages_api,
                persist_exchange=Mock(),
                consume_user_tokens=Mock(),
                load_dialogue_context=Mock(return_value=[]),
            )

        self.assertGreaterEqual(
            messages_api.method_calls.count(call.set_typing_activity(peer_id=321)),
            2,
        )
