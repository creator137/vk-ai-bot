from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.users.models import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_vk_user_id(self, vk_user_id: int) -> User | None:
        statement = select(User).where(User.vk_user_id == vk_user_id)
        return self._session.execute(statement).scalar_one_or_none()

    def create(self, vk_user_id: int) -> User:
        user = User(vk_user_id=vk_user_id)
        self._session.add(user)
        self._session.flush()
        return user

