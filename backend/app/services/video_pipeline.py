from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FrameRoi, Video
from app.services.face_detector import FaceDetector


@dataclass(frozen=True)
class PipelineResult:
    fps: int | None
    frame_count: int
    duration_sec: int | None


def _frame_time_ms(frame) -> int | None:
    if frame.pts is None or frame.time_base is None:
        return None
    return int(float(frame.pts * frame.time_base) * 1000.0)


async def process_video_to_mp4(
    *,
    video: Video,
    input_path: Path,
    output_path: Path,
    db: AsyncSession,
) -> PipelineResult:
    """
    Decode input video, detect 1 face per frame, store ROI rows, and encode an annotated MP4.
    """

    detector = FaceDetector()
    tmp_out = output_path.with_suffix(f".tmp-{uuid.uuid4().hex}.mp4")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    frame_rois: list[FrameRoi] = []

    in_container = av.open(str(input_path))
    try:
        in_stream = next((s for s in in_container.streams if s.type == "video"), None)
        if in_stream is None:
            raise ValueError("No video stream found")

        # Prefer declared fps; fallback to 30 for encoding.
        fps = None
        if in_stream.average_rate is not None:
            try:
                fps = int(round(float(in_stream.average_rate)))
            except Exception:
                fps = None
        encode_fps = fps or 30

        out_container = av.open(str(tmp_out), mode="w")
        try:
            out_stream = out_container.add_stream("libx264", rate=encode_fps)
            out_stream.pix_fmt = "yuv420p"

            frame_index = 0
            for frame in in_container.decode(in_stream):
                rgb = frame.to_ndarray(format="rgb24")
                height, width, _ = rgb.shape

                det = detector.detect_one(rgb, width=width, height=height)
                if det is None:
                    frame_rois.append(
                        FrameRoi(
                            video_id=video.id,
                            frame_index=frame_index,
                            t_ms=_frame_time_ms(frame),
                            x=None,
                            y=None,
                            w=None,
                            h=None,
                            confidence=None,
                        )
                    )
                    annotated = rgb
                else:
                    frame_rois.append(
                        FrameRoi(
                            video_id=video.id,
                            frame_index=frame_index,
                            t_ms=_frame_time_ms(frame),
                            x=det.x,
                            y=det.y,
                            w=det.w,
                            h=det.h,
                            confidence=det.score,
                        )
                    )

                    img = Image.fromarray(rgb)
                    draw = ImageDraw.Draw(img)
                    draw.rectangle(
                        [det.x, det.y, det.x + det.w, det.y + det.h],
                        outline=(0, 255, 0),
                        width=3,
                    )
                    annotated = np.asarray(img)

                av_frame = av.VideoFrame.from_ndarray(annotated, format="rgb24")
                for packet in out_stream.encode(av_frame):
                    out_container.mux(packet)

                frame_index += 1

            for packet in out_stream.encode():
                out_container.mux(packet)
        finally:
            out_container.close()

    finally:
        in_container.close()

    # Write DB rows and finalize output atomically.
    # Replace any existing ROI rows for this video (idempotent reprocessing).
    await db.execute(
        FrameRoi.__table__.delete().where(FrameRoi.video_id == video.id)  
    )
    db.add_all(frame_rois)

    video.frame_count = len(frame_rois)
    video.fps = fps
    video.duration_sec = None
    video.status = "ready"
    video.error_message = None

    await db.commit()

    tmp_out.replace(output_path)
    return PipelineResult(fps=fps, frame_count=len(frame_rois), duration_sec=None)

