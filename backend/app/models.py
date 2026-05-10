import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    original_filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str] = mapped_column(String(128))

    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="processing", index=True)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    rois: Mapped[list["FrameRoi"]] = relationship(back_populates="video", cascade="all, delete-orphan")


class FrameRoi(Base):
    __tablename__ = "frame_rois"
    __table_args__ = (
        UniqueConstraint("video_id", "frame_index", name="uq_frame_rois_video_frame_index"),
        CheckConstraint("w IS NULL OR w > 0", name="ck_frame_rois_w_gt_0_or_null"),
        CheckConstraint("h IS NULL OR h > 0", name="ck_frame_rois_h_gt_0_or_null"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), index=True)

    frame_index: Mapped[int] = mapped_column(Integer)
    t_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Pixel coordinates. When no face is detected: store NULLs (keeps stable alignment).
    x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    w: Mapped[int | None] = mapped_column(Integer, nullable=True)
    h: Mapped[int | None] = mapped_column(Integer, nullable=True)

    confidence: Mapped[float | None] = mapped_column(nullable=True)

    video: Mapped[Video] = relationship(back_populates="rois")

