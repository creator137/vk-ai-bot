from __future__ import annotations

import unittest

import httpx

from app.ai.provider import (
    ClaudeMessagesTextProvider,
    GeminiGenerateContentProvider,
    OpenAIResponsesTextProvider,
)


class AIProviderTests(unittest.TestCase):
    def test_openai_provider_extracts_text(self) -> None:
        provider = OpenAIResponsesTextProvider(
            api_key="test-key",
            model="gpt-5-mini",
            client=_MockClient(
                _build_response(
                    "https://api.openai.com/v1/responses",
                    {
                        "output": [
                            {
                                "content": [
                                    {
                                        "type": "output_text",
                                        "text": "Hello from OpenAI",
                                    }
                                ]
                            }
                        ]
                    },
                )
            ),
        )

        self.assertEqual(provider.generate_text("hello"), "Hello from OpenAI")

    def test_gemini_provider_extracts_text(self) -> None:
        provider = GeminiGenerateContentProvider(
            api_key="test-key",
            model="gemini-2.5-flash",
            client=_MockClient(
                _build_response(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                    {
                        "candidates": [
                            {
                                "content": {
                                    "parts": [
                                        {
                                            "text": "Privet from Gemini",
                                        }
                                    ]
                                }
                            }
                        ]
                    },
                )
            ),
        )

        self.assertEqual(provider.generate_text("hello"), "Privet from Gemini")

    def test_claude_provider_extracts_text(self) -> None:
        provider = ClaudeMessagesTextProvider(
            api_key="test-key",
            model="claude-sonnet-4-20250514",
            client=_MockClient(
                _build_response(
                    "https://api.anthropic.com/v1/messages",
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": "Privet from Claude",
                            }
                        ]
                    },
                )
            ),
        )

        self.assertEqual(provider.generate_text("hello"), "Privet from Claude")


class _MockClient:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    def post(self, *args, **kwargs) -> httpx.Response:
        return self._response


def _build_response(url: str, body: dict[str, object]) -> httpx.Response:
    request = httpx.Request("POST", url)
    return httpx.Response(200, json=body, request=request)
