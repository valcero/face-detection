"""init schema

Revision ID: 20260510_1429
Revises: 
Create Date: 2026-05-10

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260510_1429"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("frame_count", sa.Integer(), nullable=True),
        sa.Column("fps", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="processing"),
        sa.Column("error_message", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_videos_status", "videos", ["status"])

    op.create_table(
        "frame_rois",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("frame_index", sa.Integer(), nullable=False),
        sa.Column("t_ms", sa.BigInteger(), nullable=True),
        sa.Column("x", sa.Integer(), nullable=True),
        sa.Column("y", sa.Integer(), nullable=True),
        sa.Column("w", sa.Integer(), nullable=True),
        sa.Column("h", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("video_id", "frame_index", name="uq_frame_rois_video_frame_index"),
        sa.CheckConstraint("w IS NULL OR w > 0", name="ck_frame_rois_w_gt_0_or_null"),
        sa.CheckConstraint("h IS NULL OR h > 0", name="ck_frame_rois_h_gt_0_or_null"),
    )
    op.create_index("ix_frame_rois_video_id", "frame_rois", ["video_id"])


def downgrade() -> None:
    op.drop_index("ix_frame_rois_video_id", table_name="frame_rois")
    op.drop_table("frame_rois")
    op.drop_index("ix_videos_status", table_name="videos")
    op.drop_table("videos")

