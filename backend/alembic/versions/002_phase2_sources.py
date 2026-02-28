"""Phase 2: videos -> sources, content_payload JSONB

Revision ID: 002
Revises: 001
Create Date: 2026-02-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- sources table (rename videos -> sources) ---
    op.rename_table("videos", "sources")
    op.add_column(
        "sources",
        sa.Column(
            "source_type",
            sa.String(length=20),
            nullable=False,
            server_default="youtube",
        ),
    )
    op.add_column(
        "sources",
        sa.Column("file_path", sa.Text(), nullable=True),
    )
    op.alter_column("sources", "url", nullable=True)

    # --- transcripts: video_id -> source_id ---
    op.drop_constraint("transcripts_video_id_fkey", "transcripts", type_="foreignkey")
    op.drop_constraint("transcripts_video_id_key", "transcripts", type_="unique")
    op.alter_column("transcripts", "video_id", new_column_name="source_id")
    op.create_unique_constraint("transcripts_source_id_key", "transcripts", ["source_id"])
    op.create_foreign_key(
        "transcripts_source_id_fkey", "transcripts", "sources",
        ["source_id"], ["id"],
    )
    op.alter_column("transcripts", "source", new_column_name="source_label")

    # --- generated_content: video_id -> source_id, flat cols -> content_payload ---
    op.drop_constraint(
        "generated_content_video_id_fkey", "generated_content", type_="foreignkey"
    )
    op.drop_constraint(
        "generated_content_video_id_key", "generated_content", type_="unique"
    )
    op.alter_column("generated_content", "video_id", new_column_name="source_id")
    op.create_unique_constraint(
        "generated_content_source_id_key", "generated_content", ["source_id"]
    )
    op.create_foreign_key(
        "generated_content_source_id_fkey", "generated_content", "sources",
        ["source_id"], ["id"],
    )

    # Migrate existing flat columns into content_payload JSONB
    op.add_column(
        "generated_content",
        sa.Column("content_payload", postgresql.JSONB(), nullable=True),
    )
    op.execute(
        """
        UPDATE generated_content
        SET content_payload = jsonb_build_object(
            'medium_text', medium_text,
            'habr_text', habr_text,
            'linkedin_text', linkedin_text,
            'reduce_summary_text', reduce_summary_text
        )
        """
    )
    op.alter_column("generated_content", "content_payload", nullable=False)
    op.drop_column("generated_content", "medium_text")
    op.drop_column("generated_content", "habr_text")
    op.drop_column("generated_content", "linkedin_text")
    op.drop_column("generated_content", "reduce_summary_text")

    # --- validations: video_id -> source_id ---
    op.drop_constraint("validations_video_id_fkey", "validations", type_="foreignkey")
    op.alter_column("validations", "video_id", new_column_name="source_id")
    op.create_foreign_key(
        "validations_source_id_fkey", "validations", "sources",
        ["source_id"], ["id"],
    )


def downgrade() -> None:
    # --- validations ---
    op.drop_constraint("validations_source_id_fkey", "validations", type_="foreignkey")
    op.alter_column("validations", "source_id", new_column_name="video_id")
    op.create_foreign_key(
        "validations_video_id_fkey", "validations", "videos",
        ["video_id"], ["id"],
    )

    # --- generated_content ---
    op.add_column(
        "generated_content",
        sa.Column("medium_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "generated_content",
        sa.Column("habr_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "generated_content",
        sa.Column("linkedin_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "generated_content",
        sa.Column("reduce_summary_text", sa.Text(), nullable=True),
    )
    op.execute(
        """
        UPDATE generated_content
        SET medium_text = content_payload->>'medium_text',
            habr_text = content_payload->>'habr_text',
            linkedin_text = content_payload->>'linkedin_text',
            reduce_summary_text = content_payload->>'reduce_summary_text'
        """
    )
    op.alter_column("generated_content", "medium_text", nullable=False)
    op.alter_column("generated_content", "habr_text", nullable=False)
    op.alter_column("generated_content", "linkedin_text", nullable=False)
    op.drop_column("generated_content", "content_payload")

    op.drop_constraint(
        "generated_content_source_id_fkey", "generated_content", type_="foreignkey"
    )
    op.drop_constraint(
        "generated_content_source_id_key", "generated_content", type_="unique"
    )
    op.alter_column("generated_content", "source_id", new_column_name="video_id")
    op.create_unique_constraint(
        "generated_content_video_id_key", "generated_content", ["video_id"]
    )
    op.create_foreign_key(
        "generated_content_video_id_fkey", "generated_content", "videos",
        ["video_id"], ["id"],
    )

    # --- transcripts ---
    op.drop_constraint("transcripts_source_id_fkey", "transcripts", type_="foreignkey")
    op.drop_constraint("transcripts_source_id_key", "transcripts", type_="unique")
    op.alter_column("transcripts", "source_label", new_column_name="source")
    op.alter_column("transcripts", "source_id", new_column_name="video_id")
    op.create_unique_constraint("transcripts_video_id_key", "transcripts", ["video_id"])
    op.create_foreign_key(
        "transcripts_video_id_fkey", "transcripts", "videos",
        ["video_id"], ["id"],
    )

    # --- sources -> videos ---
    op.alter_column("sources", "url", nullable=False)
    op.drop_column("sources", "file_path")
    op.drop_column("sources", "source_type")
    op.rename_table("sources", "videos")
