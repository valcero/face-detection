import uuid
from pathlib import Path

import av
import numpy as np
import pytest

from app.models import Video
from app.services.video_pipeline import process_video_to_mp4


class FakeAsyncSession:
    def __init__(self) -> None:
        self.added = []
        self.executed = []
        self.commits = 0

    async def execute(self, stmt):
        self.executed.append(stmt)

    def add_all(self, rows):
        self.added.extend(list(rows))

    async def commit(self):
        self.commits += 1


class StubDetector:
    def detect_one(self, rgb_image, width: int, height: int):
        # Always return a box near the center (10% margin).
        x = int(width * 0.1)
        y = int(height * 0.1)
        w = int(width * 0.3)
        h = int(height * 0.3)
        return type("Det", (), {"x": x, "y": y, "w": w, "h": h, "score": 0.9})()


def _write_tiny_video(path: Path, *, frames: int = 3, w: int = 160, h: int = 120, fps: int = 10) -> None:
    container = av.open(str(path), mode="w")
    stream = container.add_stream("mpeg4", rate=fps)
    stream.width = w
    stream.height = h
    stream.pix_fmt = "yuv420p"

    for i in range(frames):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:, :, 0] = (i * 60) % 255  # simple variation per frame
        frame = av.VideoFrame.from_ndarray(img, format="rgb24")
        for packet in stream.encode(frame):
            container.mux(packet)
    for packet in stream.encode():
        container.mux(packet)
    container.close()


@pytest.mark.asyncio
async def test_pipeline_writes_output_and_rois(tmp_path: Path):
    input_path = tmp_path / "in.mp4"
    output_path = tmp_path / "out.mp4"
    _write_tiny_video(input_path)

    video = Video(
        id=uuid.uuid4(),
        original_filename="in.mp4",
        content_type="video/mp4",
        status="processing",
    )
    db = FakeAsyncSession()

    result = await process_video_to_mp4(
        video=video,
        input_path=input_path,
        output_path=output_path,
        db=db,  # fake session
        detector=StubDetector(),
    )

    assert output_path.exists()
    assert result.frame_count == 3
    assert video.status == "ready"
    assert len(db.added) == 3  # 1 ROI row per frame

