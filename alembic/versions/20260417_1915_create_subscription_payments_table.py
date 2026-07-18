"""create subscription payments table

Revision ID: 20260417_1915
Revises: 20260415_1245
Create Date: 2026-04-17 19:15:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260417_1915"
down_revision = "20260415_1245"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="robokassa"),
        sa.Column("plan_code", sa.String(length=32), nullable=False),
        sa.Column("amount_rub", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("subscription_payments")
