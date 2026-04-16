from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.internal_access import router as internal_access_router
from app.api.routes.internal_subscriptions import router as internal_subscriptions_router
from app.api.routes.vk import router as vk_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(internal_access_router)
api_router.include_router(internal_subscriptions_router)
api_router.include_router(vk_router)
