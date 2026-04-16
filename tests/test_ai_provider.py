from __future__ import annotations

import unittest

import httpx

from app.ai.provider import (
    ClaudeMessagesTextProvider,
    GeminiGenerateContentProvider,
    OpenAIResponsesTextProvider,
    TextGenerationResult,
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
                        "usage": {
                            "input_tokens": 12,
                            "output_tokens": 7,
                        },
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

        self.assertEqual(
            provider.generate_text("hello"),
            TextGenerationResult(
                text="Hello from OpenAI",
                input_tokens=12,
                output_tokens=7,
            ),
        )

    def test_gemini_provider_extracts_text(self) -> None:
        provider = GeminiGenerateContentProvider(
            api_key="test-key",
            model="gemini-2.5-flash",
            client=_MockClient(
                _build_response(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                    {
                        "usageMetadata": {
                            "promptTokenCount": 9,
                            "candidatesTokenCount": 4,
                        },
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

        self.assertEqual(
            provider.generate_text("hello"),
            TextGenerationResult(
                text="Privet from Gemini",
                input_tokens=9,
                output_tokens=4,
            ),
        )

    def test_claude_provider_extracts_text(self) -> None:
        provider = ClaudeMessagesTextProvider(
            api_key="test-key",
            model="claude-sonnet-4-20250514",
            client=_MockClient(
                _build_response(
                    "https://api.anthropic.com/v1/messages",
                    {
                        "usage": {
                            "input_tokens": 8,
                            "output_tokens": 3,
                        },
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

        self.assertEqual(
            provider.generate_text("hello"),
            TextGenerationResult(
                text="Privet from Claude",
                input_tokens=8,
                output_tokens=3,
            ),
        )


class _MockClient:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    def post(self, *args, **kwargs) -> httpx.Response:
        return self._response


def _build_response(url: str, body: dict[str, object]) -> httpx.Response:
    request = httpx.Request("POST", url)
    return httpx.Response(200, json=body, request=request)
