from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.users.models import User
from app.users.repository import UserRepository


class UserService:
    def __init__(
        self,
        session: Session,
        repository: UserRepository | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or UserRepository(session)

    def find_or_create_by_vk_user_id(self, vk_user_id: int) -> User:
        user = self._repository.get_by_vk_user_id(vk_user_id)
        if user is not None:
            return user

        try:
            user = self._repository.create(vk_user_id)
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            user = self._repository.get_by_vk_user_id(vk_user_id)
            if user is None:
                raise
        else:
            self._session.refresh(user)

        return user

