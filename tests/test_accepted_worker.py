from __future__ import annotations

import unittest
from unittest.mock import Mock

from app.ai.provider import TextGenerationResult
from app.vk_transport.keyboards import build_dialog_menu_keyboard
from app.workers.accepted_requests import run_accepted_vk_text_request


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
                Mock(request_text="Привет", response_text="Привет!"),
                Mock(request_text="Как меня зовут?", response_text="Ты не говорил имя."),
            ]
        )
        consume_user_tokens = Mock()

        run_accepted_vk_text_request(
            user_id=11,
            peer_id=321,
            text="А теперь запомни, что я Антон",
            provider=provider,
            messages_api=messages_api,
            persist_exchange=persist_exchange,
            consume_user_tokens=consume_user_tokens,
            load_dialogue_context=load_dialogue_context,
        )

        sent_prompt = provider.generate_text.call_args.args[0]
        self.assertIn("Краткая история переписки:", sent_prompt)
        self.assertIn("Пользователь: Привет", sent_prompt)
        self.assertIn("Бот: Привет!", sent_prompt)
        self.assertIn("А теперь запомни, что я Антон", sent_prompt)
