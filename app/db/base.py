from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for future SQLAlchemy models."""


# Import model modules so metadata is populated for migrations and tests.
from app.users import models as users_models  # noqa: E402,F401
