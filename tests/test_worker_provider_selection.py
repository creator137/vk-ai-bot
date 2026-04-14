from __future__ import annotations

import unittest
from unittest.mock import patch

from app.core.config import Settings
from app.workers.accepted_requests import _build_text_provider


class WorkerProviderSelectionTests(unittest.TestCase):
    def test_builds_openai_provider_when_selected(self) -> None:
        settings = Settings(
            ai_provider="openai",
            openai_api_key="openai-key",
            openai_model="gpt-5-mini",
        )

        provider = _build_text_provider(settings, peer_id=321)

        self.assertEqual(provider.__class__.__name__, "OpenAIResponsesTextProvider")

    def test_builds_gemini_provider_when_selected(self) -> None:
        settings = Settings(
            ai_provider="gemini",
            gemini_api_key="gemini-key",
            gemini_model="gemini-2.5-flash",
        )

        provider = _build_text_provider(settings, peer_id=321)

        self.assertEqual(provider.__class__.__name__, "GeminiGenerateContentProvider")

    def test_returns_none_when_selected_provider_key_is_missing(self) -> None:
        settings = Settings(ai_provider="gemini", gemini_api_key=None)

        with patch("app.workers.accepted_requests.logger.warning") as logger_warning:
            provider = _build_text_provider(settings, peer_id=321)

        self.assertIsNone(provider)
        self.assertTrue(
            any("missing_gemini_api_key" in call.args[0] for call in logger_warning.call_args_list)
        )
