from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access.models import AccessGrant


class AccessGrantRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_user_id(self, user_id: int) -> AccessGrant | None:
        statement = select(AccessGrant).where(AccessGrant.user_id == user_id)
        return self._session.execute(statement).scalar_one_or_none()

    def has_grant_for_user_id(self, user_id: int) -> bool:
        return self.get_by_user_id(user_id) is not None

    def create_for_user_id(self, user_id: int) -> AccessGrant:
        grant = AccessGrant(user_id=user_id)
        self._session.add(grant)
        self._session.flush()
        return grant
