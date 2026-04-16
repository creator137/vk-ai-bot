from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.provider_catalog import get_provider_option
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

    def set_selected_provider(self, *, user_id: int, provider_code: str) -> User:
        get_provider_option(provider_code)
        user = self._repository.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User not found: {user_id}")

        user.selected_provider = provider_code
        self._session.commit()
        self._session.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> User | None:
        return self._repository.get_by_id(user_id)
