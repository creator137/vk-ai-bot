from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.access.repository import AccessGrantRepository
from app.access.service import AccessDecision, AccessService
from app.users.service import UserService
from app.vk_transport.schemas import NormalizedVkEvent

logger = logging.getLogger(__name__)


class VkEventApplicationHandler:
    def __init__(
        self,
        user_service: UserService,
        access_service: AccessService,
    ) -> None:
        self._user_service = user_service
        self._access_service = access_service

    def handle(self, event: NormalizedVkEvent) -> AccessDecision | None:
        if event.actor_id is None:
            logger.info(
                "VK event skipped: type=%s event_id=%s has no actor_id",
                event.event_type,
                event.event_id,
            )
            return None

        user = self._user_service.find_or_create_by_vk_user_id(event.actor_id)
        decision = self._access_service.decide_for_user_id(user.id)
        logger.info(
            (
                "VK event access decided: type=%s event_id=%s user_id=%s "
                "vk_user_id=%s allowed=%s reason=%s"
            ),
            event.event_type,
            event.event_id,
            user.id,
            user.vk_user_id,
            decision.allowed,
            decision.reason,
        )
        return decision


def build_vk_event_application_handler(session: Session) -> VkEventApplicationHandler:
    user_service = UserService(session=session)
    access_repository = AccessGrantRepository(session)
    access_service = AccessService(repository=access_repository)
    return VkEventApplicationHandler(
        user_service=user_service,
        access_service=access_service,
    )
