"""add selected provider to users

Revision ID: 20260415_1245
Revises: 20260415_1115
Create Date: 2026-04-15 12:45:00
"""

from alembic import op
import sqlalchemy as sa

revision = "20260415_1245"
down_revision = "20260415_1115"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("selected_provider", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "selected_provider")
