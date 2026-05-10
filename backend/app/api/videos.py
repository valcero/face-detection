from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from app.api.schemas import RoiFrame, RoiResponse, VideoCreateResponse
from app.db import get_db_session
from app.models import FrameRoi, Video
from app.settings import settings
from app.services.video_pipeline import process_video_to_mp4


router = APIRouter(prefix="/api/videos", tags=["videos"])

_ALLOWED_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "application/octet-stream",  # some browsers/tools mislabel
}


def _ensure_dirs() -> None:
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)


def _raw_path(video_id: uuid.UUID, suffix: str) -> Path:
    return settings.raw_dir / f"{video_id}{suffix}"


def _processed_path(video_id: uuid.UUID) -> Path:
    return settings.processed_dir / f"{video_id}.mp4"


@router.post("", status_code=status.HTTP_201_CREATED, response_model=VideoCreateResponse)
async def create_video(
    response: Response,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
) -> VideoCreateResponse:
    _ensure_dirs()

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported content type")

    original_name = file.filename or "upload"
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".mp4", ".webm", ".mov"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported file extension")

    video = Video(original_filename=original_name, content_type=content_type or "application/octet-stream", status="processing")
    db.add(video)
    await db.commit()
    await db.refresh(video)

    max_bytes = settings.max_upload_mb * 1024 * 1024
    dst = _raw_path(video.id, suffix)

    written = 0
    try:
        with dst.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
                f.write(chunk)
    except HTTPException:
        # Cleanup and mark failed if  already created the record.
        if dst.exists():
            try:
                dst.unlink()
            except OSError:
                pass
        video.status = "failed"
        video.error_message = "upload rejected"
        await db.commit()
        raise
    except Exception as e:
        if dst.exists():
            try:
                dst.unlink()
            except OSError:
                pass
        video.status = "failed"
        video.error_message = f"upload failed: {e.__class__.__name__}"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload failed") from e

    # Synchronous pipeline for short demo clips: raw → processed, and fill ROI rows.
    try:
        await process_video_to_mp4(video=video, input_path=dst, output_path=_processed_path(video.id), db=db)
    except Exception as e:
        video.status = "failed"
        video.error_message = f"processing failed: {e.__class__.__name__}"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Video processing failed") from e

    response.headers["Location"] = f"/api/videos/{video.id}/stream"
    return VideoCreateResponse(video_id=str(video.id), status=video.status)


@router.get("/{video_id}/stream")
async def stream_video(video_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)) -> FileResponse:
    video = await db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if video.status != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Video status is {video.status}")

    path = _processed_path(video_id)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Processed video missing")

    return FileResponse(
        path=str(path),
        media_type="video/mp4",
        filename=f"{video_id}.mp4",
    )


@router.get("/{video_id}/roi", response_model=RoiResponse)
async def get_roi(video_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)) -> RoiResponse:
    video = await db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    res = await db.execute(
        select(FrameRoi).where(FrameRoi.video_id == video_id).order_by(FrameRoi.frame_index.asc())
    )
    rows = list(res.scalars().all())
    frames = [
        RoiFrame(
            i=r.frame_index,
            t_ms=r.t_ms,
            x=r.x,
            y=r.y,
            w=r.w,
            h=r.h,
            score=r.confidence,
        )
        for r in rows
    ]
    return RoiResponse(video_id=str(video_id), fps=video.fps, frames=frames)

