from __future__ import annotations

from secrets import randbelow
from typing import Any

import httpx


class VkApiError(RuntimeError):
    """Raised when VK API responds with an error payload."""


class VkMessagesApi:
    def __init__(
        self,
        token: str,
        api_version: str,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._token = token
        self._api_version = api_version
        self._client = client

    def send_text_message(self, *, peer_id: int, text: str) -> None:
        payload = {
            "peer_id": peer_id,
            "message": text,
            "random_id": _generate_random_id(),
            "access_token": self._token,
            "v": self._api_version,
        }

        response = self._post("https://api.vk.com/method/messages.send", data=payload)
        response.raise_for_status()
        body = response.json()

        if "error" in body:
            error = body["error"]
            code = error.get("error_code", "unknown")
            message = error.get("error_msg", "unknown VK API error")
            raise VkApiError(f"VK API error {code}: {message}")

        if "response" not in body:
            raise VkApiError("VK API returned unexpected payload for messages.send")

    def _post(self, url: str, *, data: dict[str, Any]) -> httpx.Response:
        if self._client is not None:
            return self._client.post(url, data=data, timeout=10.0)

        with httpx.Client() as client:
            return client.post(url, data=data, timeout=10.0)


def _generate_random_id() -> int:
    return randbelow(2_147_483_647)
