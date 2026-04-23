from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_subscriptions_user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_code: Mapped[str] = mapped_column(String(32), nullable=False)
    included_tokens: Mapped[int] = mapped_column(nullable=False)
    used_tokens: Mapped[int] = mapped_column(nullable=False, server_default="0")
    daily_tokens_last_issued_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
