"""create user subscriptions and request usage columns

Revision ID: 20260415_1115
Revises: 20260414_1515
Create Date: 2026-04-15 11:15:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260415_1115"
down_revision = "20260414_1515"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_code", sa.String(length=32), nullable=False),
        sa.Column("included_tokens", sa.Integer(), nullable=False),
        sa.Column("used_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_subscriptions_user_id"),
    )
    op.add_column(
        "accepted_request_records",
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "accepted_request_records",
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "accepted_request_records",
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("accepted_request_records", "total_tokens")
    op.drop_column("accepted_request_records", "output_tokens")
    op.drop_column("accepted_request_records", "input_tokens")
    op.drop_table("user_subscriptions")
