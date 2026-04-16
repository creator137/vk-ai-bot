from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class OpenAIProviderError(RuntimeError):
    """Raised when the OpenAI API request or payload is invalid for this flow."""


class GeminiProviderError(RuntimeError):
    """Raised when the Gemini API request or payload is invalid for this flow."""


class ClaudeProviderError(RuntimeError):
    """Raised when the Claude API request or payload is invalid for this flow."""


class TextGenerationProvider(Protocol):
    def generate_text(self, prompt: str) -> "TextGenerationResult": ...


@dataclass(frozen=True, slots=True)
class TextGenerationResult:
    text: str
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class OpenAIResponsesTextProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client

    def generate_text(self, prompt: str) -> TextGenerationResult:
        response = self._post(
            "https://api.openai.com/v1/responses",
            json={
                "model": self._model,
                "input": prompt,
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise OpenAIProviderError(_build_http_error_message(error.response)) from error

        body = response.json()
        error_payload = body.get("error")
        if isinstance(error_payload, dict):
            message = error_payload.get("message")
            if isinstance(message, str) and message:
                raise OpenAIProviderError(message)
            raise OpenAIProviderError("OpenAI API returned an error payload")

        text = _extract_output_text(body)
        if not text:
            raise OpenAIProviderError("OpenAI response did not contain output text")

        usage = _extract_openai_usage(body)
        return TextGenerationResult(
            text=text,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
        )

    def _post(self, url: str, *, json: dict[str, Any]) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._client is not None:
            return self._client.post(url, headers=headers, json=json, timeout=30.0)

        with httpx.Client() as client:
            return client.post(url, headers=headers, json=json, timeout=30.0)


class GeminiGenerateContentProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client

    def generate_text(self, prompt: str) -> TextGenerationResult:
        response = self._post(
            (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self._model}:generateContent"
            ),
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt,
                            }
                        ]
                    }
                ]
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise GeminiProviderError(_build_http_error_message(error.response)) from error

        body = response.json()
        error_payload = body.get("error")
        if isinstance(error_payload, dict):
            message = error_payload.get("message")
            if isinstance(message, str) and message:
                raise GeminiProviderError(message)
            raise GeminiProviderError("Gemini API returned an error payload")

        text = _extract_gemini_output_text(body)
        if not text:
            raise GeminiProviderError("Gemini response did not contain output text")

        usage = _extract_gemini_usage(body)
        return TextGenerationResult(
            text=text,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
        )

    def _post(self, url: str, *, json: dict[str, Any]) -> httpx.Response:
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        if self._client is not None:
            return self._client.post(url, headers=headers, json=json, timeout=30.0)

        with httpx.Client() as client:
            return client.post(url, headers=headers, json=json, timeout=30.0)


class ClaudeMessagesTextProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client

    def generate_text(self, prompt: str) -> TextGenerationResult:
        response = self._post(
            "https://api.anthropic.com/v1/messages",
            json={
                "model": self._model,
                "max_tokens": 256,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise ClaudeProviderError(_build_http_error_message(error.response)) from error

        body = response.json()
        error_payload = body.get("error")
        if isinstance(error_payload, dict):
            message = error_payload.get("message")
            if isinstance(message, str) and message:
                raise ClaudeProviderError(message)
            raise ClaudeProviderError("Claude API returned an error payload")

        text = _extract_claude_output_text(body)
        if not text:
            raise ClaudeProviderError("Claude response did not contain output text")

        usage = _extract_claude_usage(body)
        return TextGenerationResult(
            text=text,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
        )

    def _post(self, url: str, *, json: dict[str, Any]) -> httpx.Response:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        if self._client is not None:
            return self._client.post(url, headers=headers, json=json, timeout=30.0)

        with httpx.Client() as client:
            return client.post(url, headers=headers, json=json, timeout=30.0)


def _extract_output_text(body: dict[str, Any]) -> str:
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = body.get("output")
    if not isinstance(output, list):
        return ""

    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue

        content = item.get("content")
        if not isinstance(content, list):
            continue

        for content_item in content:
            if not isinstance(content_item, dict):
                continue
            if content_item.get("type") != "output_text":
                continue
            text = content_item.get("text")
            if isinstance(text, str) and text:
                parts.append(text)

    return "".join(parts).strip()


def _extract_gemini_output_text(body: dict[str, Any]) -> str:
    candidates = body.get("candidates")
    if not isinstance(candidates, list):
        return ""

    parts: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue

        content = candidate.get("content")
        if not isinstance(content, dict):
            continue

        content_parts = content.get("parts")
        if not isinstance(content_parts, list):
            continue

        for part in content_parts:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str) and text:
                parts.append(text)

    return "".join(parts).strip()


def _extract_openai_usage(body: dict[str, Any]) -> dict[str, int]:
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return {"input_tokens": 0, "output_tokens": 0}

    return {
        "input_tokens": _extract_non_negative_int(usage.get("input_tokens")),
        "output_tokens": _extract_non_negative_int(usage.get("output_tokens")),
    }


def _extract_gemini_usage(body: dict[str, Any]) -> dict[str, int]:
    usage = body.get("usageMetadata")
    if not isinstance(usage, dict):
        return {"input_tokens": 0, "output_tokens": 0}

    return {
        "input_tokens": _extract_non_negative_int(usage.get("promptTokenCount")),
        "output_tokens": _extract_non_negative_int(usage.get("candidatesTokenCount")),
    }


def _extract_claude_output_text(body: dict[str, Any]) -> str:
    content = body.get("content")
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "text":
            continue
        text = item.get("text")
        if isinstance(text, str) and text:
            parts.append(text)

    return "".join(parts).strip()


def _extract_claude_usage(body: dict[str, Any]) -> dict[str, int]:
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return {"input_tokens": 0, "output_tokens": 0}

    return {
        "input_tokens": _extract_non_negative_int(usage.get("input_tokens")),
        "output_tokens": _extract_non_negative_int(usage.get("output_tokens")),
    }


def _extract_non_negative_int(value: Any) -> int:
    if isinstance(value, int) and value >= 0:
        return value
    return 0


def _build_http_error_message(response: httpx.Response) -> str:
    message = f"AI provider request failed with status {response.status_code}"
    try:
        body = response.json()
    except ValueError:
        return message

    error_payload = body.get("error")
    if not isinstance(error_payload, dict):
        return message

    error_message = error_payload.get("message")
    if isinstance(error_message, str) and error_message:
        return f"{message}: {error_message}"

    return message
