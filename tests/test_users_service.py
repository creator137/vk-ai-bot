from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.users.models import User
from app.users.repository import UserRepository
from app.users.service import UserService


class UsersBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
        )
        Base.metadata.create_all(self.engine)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_find_or_create_creates_user_when_missing(self) -> None:
        with self.session_factory() as session:
            service = UserService(session)
            user = service.find_or_create_by_vk_user_id(123456)

            self.assertIsNotNone(user.id)
            self.assertEqual(user.vk_user_id, 123456)
            self.assertEqual(self._count_users(session), 1)

    def test_find_or_create_returns_existing_user(self) -> None:
        with self.session_factory() as session:
            service = UserService(session)
            first_user = service.find_or_create_by_vk_user_id(123456)
            second_user = service.find_or_create_by_vk_user_id(123456)

            self.assertEqual(second_user.id, first_user.id)
            self.assertEqual(self._count_users(session), 1)

    def test_repository_create_respects_unique_vk_user_id(self) -> None:
        with self.session_factory() as first_session:
            first_repository = UserRepository(first_session)
            first_repository.create(123456)
            first_session.commit()

        with self.session_factory() as second_session:
            second_repository = UserRepository(second_session)

            with self.assertRaises(IntegrityError):
                second_repository.create(123456)

    def test_set_selected_provider_updates_user(self) -> None:
        with self.session_factory() as session:
            service = UserService(session)
            user = service.find_or_create_by_vk_user_id(123456)

            updated = service.set_selected_provider(
                user_id=user.id,
                provider_code="gemini",
            )

        self.assertEqual(updated.selected_provider, "gemini")

    @staticmethod
    def _count_users(session: Session) -> int:
        return len(session.execute(select(User)).scalars().all())
