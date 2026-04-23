"""add daily tokens issuance date to user subscriptions

Revision ID: 20260423_1025
Revises: 20260417_1915
Create Date: 2026-04-23 10:25:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260423_1025"
down_revision = "20260417_1915"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_subscriptions",
        sa.Column("daily_tokens_last_issued_at", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_subscriptions", "daily_tokens_last_issued_at")
