from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.access.repository import AccessGrantRepository
from app.access.service import AccessDecision, AccessService
from app.application.request_outcomes import RequestOutcome
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

    def handle(self, event: NormalizedVkEvent) -> RequestOutcome:
        if event.actor_id is None:
            outcome = RequestOutcome(status="skipped", reason="missing_actor_id")
            logger.info(
                "VK event skipped: type=%s event_id=%s reason=%s",
                event.event_type,
                event.event_id,
                outcome.reason,
            )
            return outcome

        user = self._user_service.find_or_create_by_vk_user_id(event.actor_id)
        decision = self._access_service.decide_for_user_id(user.id)
        outcome = _map_access_decision_to_outcome(user.id, decision)
        logger.info(
            (
                "VK event outcome decided: type=%s event_id=%s user_id=%s "
                "vk_user_id=%s status=%s reason=%s"
            ),
            event.event_type,
            event.event_id,
            user.id,
            user.vk_user_id,
            outcome.status,
            outcome.reason,
        )
        return outcome


def _map_access_decision_to_outcome(
    user_id: int,
    decision: AccessDecision,
) -> RequestOutcome:
    if decision.allowed:
        return RequestOutcome(
            status="accepted",
            reason="access_allowed",
            user_id=user_id,
        )

    return RequestOutcome(
        status="denied",
        reason="access_denied",
        user_id=user_id,
    )


def build_vk_event_application_handler(session: Session) -> VkEventApplicationHandler:
    user_service = UserService(session=session)
    access_repository = AccessGrantRepository(session)
    access_service = AccessService(repository=access_repository)
    return VkEventApplicationHandler(
        user_service=user_service,
        access_service=access_service,
    )
