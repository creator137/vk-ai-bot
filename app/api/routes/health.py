from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Literal

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db.session import check_database
from app.infra.redis import check_redis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "unhealthy"]
    checks: dict[str, str]


def _run_check(name: str, checker: Callable[[], None], checks: dict[str, str]) -> bool:
    try:
        checker()
        checks[name] = "ok"
        return True
    except Exception as exc:
        logger.warning("%s healthcheck failed: %s", name, exc)
        checks[name] = "error"
        return False


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse | JSONResponse:
    checks: dict[str, str] = {}

    postgres_ok = _run_check("postgres", check_database, checks)
    redis_ok = _run_check("redis", check_redis, checks)

    if postgres_ok and redis_ok:
        return HealthResponse(status="ok", checks=checks)

    payload = HealthResponse(status="unhealthy", checks=checks).model_dump()
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=payload)
