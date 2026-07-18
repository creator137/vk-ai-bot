from __future__ import annotations

from redis import Redis

from app.core.config import get_settings

_client: Redis | None = None


def get_redis_client() -> Redis:
    global _client
    if _client is None:
        settings = get_settings()
        _client = Redis.from_url(settings.redis_url)
    return _client


def check_redis() -> None:
    get_redis_client().ping()


def close_redis_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None

