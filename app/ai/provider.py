from __future__ import annotations

from typing import Any

import httpx


class OpenAIProviderError(RuntimeError):
    """Raised when the OpenAI API request or payload is invalid for this flow."""


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

    def generate_text(self, prompt: str) -> str:
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

        return text

    def _post(self, url: str, *, json: dict[str, Any]) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
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


def _build_http_error_message(response: httpx.Response) -> str:
    message = f"OpenAI API request failed with status {response.status_code}"
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
