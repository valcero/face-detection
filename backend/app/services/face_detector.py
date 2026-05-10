from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import FaceDetector as MpFaceDetector
from mediapipe.tasks.python.vision import FaceDetectorOptions, RunningMode


@dataclass(frozen=True)
class Detection:
    x: int
    y: int
    w: int
    h: int
    score: float | None


class FaceDetector:
    """
    Minimal wrapper around MediaPipe Tasks FaceDetector.
    Returns an axis-aligned bounding box in pixel coordinates for a single face.
    """

    def __init__(self, model_path: str | Path = "/app/models/blaze_face_short_range.tflite") -> None:
        options = FaceDetectorOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=RunningMode.IMAGE,
        )
        self._detector = MpFaceDetector.create_from_options(options)

    def detect_one(self, rgb_image, width: int, height: int) -> Detection | None:
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
        result = self._detector.detect(image)
        if not result.detections:
            return None

        # Single-face assumption: pick the highest confidence detection.
        best = None
        best_score = -1.0
        for det in result.detections:
            score = None
            if det.categories:
                score = float(det.categories[0].score)
            if score is None:
                score = 0.0
            if score > best_score:
                best = det
                best_score = score

        if best is None:
            return None

        bbox = best.bounding_box
        x = int(bbox.origin_x)
        y = int(bbox.origin_y)
        w = int(bbox.width)
        h = int(bbox.height)

        # Clamp to frame bounds, keep non-negative.
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        w = max(1, min(w, width - x))
        h = max(1, min(h, height - y))

        return Detection(x=x, y=y, w=w, h=h, score=best_score)

