"""initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "videos",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("progress_json", postgresql.JSONB(), nullable=True),
        sa.Column("regen_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "transcripts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("video_id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("meta_json", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id"),
    )

    op.create_table(
        "generated_content",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("video_id", sa.UUID(), nullable=False),
        sa.Column("medium_text", sa.Text(), nullable=False),
        sa.Column("habr_text", sa.Text(), nullable=False),
        sa.Column("linkedin_text", sa.Text(), nullable=False),
        sa.Column("reduce_summary_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id"),
    )

    op.create_table(
        "validations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("video_id", sa.UUID(), nullable=False),
        sa.Column("overall_verdict", sa.String(length=20), nullable=False),
        sa.Column("report_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("validations")
    op.drop_table("generated_content")
    op.drop_table("transcripts")
    op.drop_table("videos")
