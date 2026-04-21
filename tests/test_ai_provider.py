from __future__ import annotations

import unittest

import httpx

from app.ai.provider import (
    ClaudeMessagesTextProvider,
    GeminiGenerateContentProvider,
    ImageInput,
    OpenAIResponsesTextProvider,
    TextGenerationResult,
)


class AIProviderTests(unittest.TestCase):
    def test_openai_provider_extracts_text(self) -> None:
        client = _RecordingMockClient(
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
                    ],
                },
            )
        )
        provider = OpenAIResponsesTextProvider(
            api_key="test-key",
            model="gpt-5-mini",
            client=client,
        )

        self.assertEqual(
            provider.generate_text("hello"),
            TextGenerationResult(
                text="Hello from OpenAI",
                input_tokens=12,
                output_tokens=7,
            ),
        )

    def test_openai_provider_sends_image_inputs(self) -> None:
        client = _RecordingMockClient(
            _build_response(
                "https://api.openai.com/v1/responses",
                {
                    "usage": {
                        "input_tokens": 15,
                        "output_tokens": 6,
                    },
                    "output": [
                        {
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": "Image reply",
                                }
                            ]
                        }
                    ],
                },
            )
        )
        provider = OpenAIResponsesTextProvider(
            api_key="test-key",
            model="gpt-5-mini",
            client=client,
        )

        result = provider.generate_text_from_images(
            prompt="Describe this image",
            images=[ImageInput(image_url="https://example.com/cat.jpg")],
        )

        self.assertEqual(
            result,
            TextGenerationResult(
                text="Image reply",
                input_tokens=15,
                output_tokens=6,
            ),
        )
        content = client.calls[0]["json"]["input"][0]["content"]
        self.assertEqual(content[0]["type"], "input_text")
        self.assertEqual(content[0]["text"], "Describe this image")
        self.assertEqual(content[1]["type"], "input_image")
        self.assertEqual(content[1]["image_url"], "https://example.com/cat.jpg")

    def test_gemini_provider_extracts_text(self) -> None:
        client = _RecordingMockClient(
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
                    ],
                },
            )
        )
        provider = GeminiGenerateContentProvider(
            api_key="test-key",
            model="gemini-2.5-flash",
            client=client,
        )

        self.assertEqual(
            provider.generate_text("hello"),
            TextGenerationResult(
                text="Privet from Gemini",
                input_tokens=9,
                output_tokens=4,
            ),
        )

    def test_gemini_provider_sends_inline_image_data(self) -> None:
        client = _RecordingMockClient(
            _build_response(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                {
                    "usageMetadata": {
                        "promptTokenCount": 10,
                        "candidatesTokenCount": 5,
                    },
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": "Gemini image reply",
                                    }
                                ]
                            }
                        }
                    ],
                },
            )
        )
        provider = GeminiGenerateContentProvider(
            api_key="test-key",
            model="gemini-2.5-flash",
            client=client,
        )

        result = provider.generate_text_from_images(
            prompt="Describe this image",
            images=[ImageInput(data=b"abc", mime_type="image/jpeg")],
        )

        self.assertEqual(
            result,
            TextGenerationResult(
                text="Gemini image reply",
                input_tokens=10,
                output_tokens=5,
            ),
        )
        parts = client.calls[0]["json"]["contents"][0]["parts"]
        self.assertEqual(parts[0]["text"], "Describe this image")
        self.assertEqual(parts[1]["inline_data"]["mime_type"], "image/jpeg")
        self.assertEqual(parts[1]["inline_data"]["data"], "YWJj")

    def test_claude_provider_extracts_text(self) -> None:
        client = _RecordingMockClient(
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
                    ],
                },
            )
        )
        provider = ClaudeMessagesTextProvider(
            api_key="test-key",
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            client=client,
        )

        self.assertEqual(
            provider.generate_text("hello"),
            TextGenerationResult(
                text="Privet from Claude",
                input_tokens=8,
                output_tokens=3,
            ),
        )
        self.assertEqual(client.calls[0]["json"]["max_tokens"], 1024)

    def test_claude_provider_sends_base64_image_data(self) -> None:
        client = _RecordingMockClient(
            _build_response(
                "https://api.anthropic.com/v1/messages",
                {
                    "usage": {
                        "input_tokens": 11,
                        "output_tokens": 5,
                    },
                    "content": [
                        {
                            "type": "text",
                            "text": "Claude image reply",
                        }
                    ],
                },
            )
        )
        provider = ClaudeMessagesTextProvider(
            api_key="test-key",
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            client=client,
        )

        result = provider.generate_text_from_images(
            prompt="Describe this image",
            images=[ImageInput(data=b"abc", mime_type="image/png")],
        )

        self.assertEqual(
            result,
            TextGenerationResult(
                text="Claude image reply",
                input_tokens=11,
                output_tokens=5,
            ),
        )
        content = client.calls[0]["json"]["messages"][0]["content"]
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[0]["text"], "Describe this image")
        self.assertEqual(content[1]["type"], "image")
        self.assertEqual(content[1]["source"]["media_type"], "image/png")
        self.assertEqual(content[1]["source"]["data"], "YWJj")
        self.assertEqual(client.calls[0]["json"]["max_tokens"], 1024)


class _RecordingMockClient:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response
        self.calls: list[dict[str, object]] = []

    def post(self, *args, **kwargs) -> httpx.Response:
        self.calls.append({"args": args, "kwargs": kwargs, **kwargs})
        return self._response


def _build_response(url: str, body: dict[str, object]) -> httpx.Response:
    request = httpx.Request("POST", url)
    return httpx.Response(200, json=body, request=request)
