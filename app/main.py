from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import dispose_engine
from app.infra.redis import close_redis_client


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)

    try:
        yield
    finally:
        close_redis_client()
        dispose_engine()
        logger.info("Stopping %s", settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.include_router(api_router)
    return application


app = create_app()

