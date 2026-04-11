from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.access.service import AccessService
from app.users.service import UserService


@dataclass(frozen=True, slots=True)
class AccessGrantIssue:
    vk_user_id: int
    user_id: int
    grant_created: bool


class AccessGrantIssuanceHandler:
    def __init__(
        self,
        user_service: UserService,
        access_service: AccessService,
    ) -> None:
        self._user_service = user_service
        self._access_service = access_service

    def issue_for_vk_user_id(self, vk_user_id: int) -> AccessGrantIssue:
        user = self._user_service.find_or_create_by_vk_user_id(vk_user_id)
        issuance = self._access_service.issue_for_user_id(user.id)
        return AccessGrantIssue(
            vk_user_id=user.vk_user_id,
            user_id=user.id,
            grant_created=issuance.created,
        )


def build_access_grant_issuance_handler(session: Session) -> AccessGrantIssuanceHandler:
    user_service = UserService(session=session)
    access_service = AccessService(session=session)
    return AccessGrantIssuanceHandler(
        user_service=user_service,
        access_service=access_service,
    )
