from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VK AI Platform"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://vk_ai:vk_ai@localhost:5432/vk_ai"
    redis_url: str = "redis://localhost:6379/0"
    ai_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    claude_api_key: str | None = None
    claude_model: str = "claude-sonnet-4-20250514"
    internal_access_token: str | None = None
    vk_outbound_token: str | None = None
    vk_api_version: str = "5.199"
    vk_callback_secret: str | None = None
    vk_callback_confirmation_token: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
