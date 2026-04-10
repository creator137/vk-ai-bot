from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.users.service import UserService
from app.vk_transport.schemas import NormalizedVkEvent

logger = logging.getLogger(__name__)


class VkEventApplicationHandler:
    def __init__(self, user_service: UserService) -> None:
        self._user_service = user_service

    def handle(self, event: NormalizedVkEvent) -> None:
        if event.actor_id is None:
            logger.info(
                "VK event skipped: type=%s event_id=%s has no actor_id",
                event.event_type,
                event.event_id,
            )
            return

        user = self._user_service.find_or_create_by_vk_user_id(event.actor_id)
        logger.info(
            "VK event linked to user: type=%s event_id=%s user_id=%s vk_user_id=%s",
            event.event_type,
            event.event_id,
            user.id,
            user.vk_user_id,
        )


def build_vk_event_application_handler(session: Session) -> VkEventApplicationHandler:
    user_service = UserService(session=session)
    return VkEventApplicationHandler(user_service=user_service)

