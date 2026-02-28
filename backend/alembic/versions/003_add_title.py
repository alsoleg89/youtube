"""Add title column to sources

Revision ID: 003
Revises: 002
Create Date: 2026-02-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("title", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sources", "title")
