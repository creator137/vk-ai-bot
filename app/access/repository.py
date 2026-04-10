from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access.models import AccessGrant


class AccessGrantRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def has_grant_for_user_id(self, user_id: int) -> bool:
        statement = select(AccessGrant.user_id).where(AccessGrant.user_id == user_id)
        return self._session.execute(statement).scalar_one_or_none() is not None
