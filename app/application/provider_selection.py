from __future__ import annotations

from dataclasses import dataclass

from app.ai.provider_catalog import (
    ProviderOption,
    find_provider_option_by_button_text,
    get_provider_option,
)
from app.users.service import UserService


@dataclass(frozen=True, slots=True)
class ProviderSelectionResult:
    user_id: int
    vk_user_id: int
    provider_code: str
    provider_title: str


class ProviderSelectionService:
    def __init__(self, user_service: UserService) -> None:
        self._user_service = user_service

    def handle_message_text(
        self,
        *,
        user_id: int,
        message_text: str | None,
    ) -> ProviderSelectionResult | None:
        if not message_text:
            return None

        option = find_provider_option_by_button_text(message_text)
        if option is None:
            return None

        return self.select_provider(user_id=user_id, provider_code=option.code)

    def select_provider(
        self,
        *,
        user_id: int,
        provider_code: str,
    ) -> ProviderSelectionResult:
        option = get_provider_option(provider_code)
        user = self._user_service.set_selected_provider(
            user_id=user_id,
            provider_code=option.code,
        )
        return _build_result(user.id, user.vk_user_id, option)


def _build_result(
    user_id: int,
    vk_user_id: int,
    option: ProviderOption,
) -> ProviderSelectionResult:
    return ProviderSelectionResult(
        user_id=user_id,
        vk_user_id=vk_user_id,
        provider_code=option.code,
        provider_title=option.title,
    )
