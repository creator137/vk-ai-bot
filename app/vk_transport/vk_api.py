from __future__ import annotations

import json
from pathlib import Path
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

    def send_text_message(
        self,
        *,
        peer_id: int,
        text: str,
        keyboard: dict[str, Any] | None = None,
        image_path: str | None = None,
    ) -> None:
        payload = {
            "peer_id": peer_id,
            "message": text,
            "random_id": _generate_random_id(),
            "access_token": self._token,
            "v": self._api_version,
        }
        if keyboard is not None:
            payload["keyboard"] = json.dumps(keyboard, ensure_ascii=False)
        if image_path is not None:
            payload["attachment"] = self._upload_message_photo(
                peer_id=peer_id,
                image_path=image_path,
            )

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

    def _upload_message_photo(
        self,
        *,
        peer_id: int,
        image_path: str,
    ) -> str:
        upload_server_response = self._post(
            "https://api.vk.com/method/photos.getMessagesUploadServer",
            data={
                "peer_id": peer_id,
                "access_token": self._token,
                "v": self._api_version,
            },
        )
        upload_server_response.raise_for_status()
        upload_server_body = upload_server_response.json()
        upload_server = _unwrap_vk_response(
            upload_server_body,
            method_name="photos.getMessagesUploadServer",
        )
        upload_url = upload_server.get("upload_url")
        if not isinstance(upload_url, str) or not upload_url:
            raise VkApiError("VK API returned unexpected payload for photos.getMessagesUploadServer")

        file_path = Path(image_path)
        with file_path.open("rb") as image_file:
            upload_response = self._post_multipart(
                upload_url,
                files={
                    "photo": (
                        file_path.name,
                        image_file,
                        "image/jpeg",
                    )
                },
            )
        upload_response.raise_for_status()
        upload_body = upload_response.json()
        server = upload_body.get("server")
        photo = upload_body.get("photo")
        hash_value = upload_body.get("hash")
        if server is None or not isinstance(photo, str) or not isinstance(hash_value, str):
            raise VkApiError("VK API returned unexpected upload payload for messages photo")

        save_response = self._post(
            "https://api.vk.com/method/photos.saveMessagesPhoto",
            data={
                "server": server,
                "photo": photo,
                "hash": hash_value,
                "access_token": self._token,
                "v": self._api_version,
            },
        )
        save_response.raise_for_status()
        save_body = save_response.json()
        saved_items = _unwrap_vk_response(
            save_body,
            method_name="photos.saveMessagesPhoto",
        )
        if not isinstance(saved_items, list) or not saved_items:
            raise VkApiError("VK API returned unexpected payload for photos.saveMessagesPhoto")

        saved_photo = saved_items[0]
        if not isinstance(saved_photo, dict):
            raise VkApiError("VK API returned unexpected payload for photos.saveMessagesPhoto")

        owner_id = saved_photo.get("owner_id")
        photo_id = saved_photo.get("id")
        access_key = saved_photo.get("access_key")
        if not isinstance(owner_id, int) or not isinstance(photo_id, int):
            raise VkApiError("VK API returned photo without owner_id/id")

        attachment = f"photo{owner_id}_{photo_id}"
        if isinstance(access_key, str) and access_key:
            attachment = f"{attachment}_{access_key}"
        return attachment

    def _post(self, url: str, *, data: dict[str, Any]) -> httpx.Response:
        if self._client is not None:
            return self._client.post(url, data=data, timeout=10.0)

        with httpx.Client() as client:
            return client.post(url, data=data, timeout=10.0)

    def _post_multipart(self, url: str, *, files: dict[str, Any]) -> httpx.Response:
        if self._client is not None:
            return self._client.post(url, files=files, timeout=30.0)

        with httpx.Client() as client:
            return client.post(url, files=files, timeout=30.0)


def _generate_random_id() -> int:
    return randbelow(2_147_483_647)


def _unwrap_vk_response(body: dict[str, Any], *, method_name: str) -> Any:
    if "error" in body:
        error = body["error"]
        code = error.get("error_code", "unknown")
        message = error.get("error_msg", "unknown VK API error")
        raise VkApiError(f"VK API error {code}: {message}")

    if "response" not in body:
        raise VkApiError(f"VK API returned unexpected payload for {method_name}")

    return body["response"]
