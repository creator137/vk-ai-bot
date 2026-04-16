from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderOption:
    code: str
    title: str
    button_text: str


CLAUDE_OPTION = ProviderOption("claude", "Claude", "🤖 Claude")
GEMINI_OPTION = ProviderOption("gemini", "Gemini", "⚡ Gemini")
CHATGPT_OPTION = ProviderOption("openai", "ChatGPT", "💬 ChatGPT")

PROVIDER_OPTIONS = (
    CLAUDE_OPTION,
    GEMINI_OPTION,
    CHATGPT_OPTION,
)

PROVIDER_BY_CODE = {option.code: option for option in PROVIDER_OPTIONS}
PROVIDER_BY_BUTTON_TEXT = {}
for option in PROVIDER_OPTIONS:
    PROVIDER_BY_BUTTON_TEXT[option.button_text.casefold()] = option
    PROVIDER_BY_BUTTON_TEXT[option.title.casefold()] = option
    PROVIDER_BY_BUTTON_TEXT[option.code.casefold()] = option


def get_provider_option(code: str) -> ProviderOption:
    try:
        return PROVIDER_BY_CODE[code]
    except KeyError as error:
        raise ValueError(f"Unsupported provider code: {code}") from error


def find_provider_option_by_button_text(text: str) -> ProviderOption | None:
    return PROVIDER_BY_BUTTON_TEXT.get(text.strip().casefold())
