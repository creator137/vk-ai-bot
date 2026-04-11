from __future__ import annotations

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from app.core.config import get_settings
from app.core.logging import configure_logging

_configured = False


def ensure_worker_broker_configured() -> None:
    global _configured
    if _configured:
        return

    settings = get_settings()
    configure_logging(settings.log_level)

    broker = RedisBroker(url=settings.redis_url)
    dramatiq.set_broker(broker)
    _configured = True


ensure_worker_broker_configured()

from app.workers import accepted_requests  # noqa: E402,F401
