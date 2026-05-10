from __future__ import annotations

from pydantic import BaseModel, Field


class VideoCreateResponse(BaseModel):
    video_id: str = Field(..., description="UUID of the created video job")
    status: str = Field(..., description="processing|ready|failed")


class RoiFrame(BaseModel):
    i: int = Field(..., description="Frame index (0-based)")
    t_ms: int | None = Field(None, description="Timestamp of frame in milliseconds")
    x: int | None = Field(None, description="Top-left X in pixels")
    y: int | None = Field(None, description="Top-left Y in pixels")
    w: int | None = Field(None, description="Width in pixels")
    h: int | None = Field(None, description="Height in pixels")
    score: float | None = Field(None, description="Detector confidence score")


class RoiResponse(BaseModel):
    video_id: str
    fps: int | None = None
    frames: list[RoiFrame]

