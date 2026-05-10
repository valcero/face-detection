from __future__ import annotations

from dataclasses import dataclass

import mediapipe as mp


@dataclass(frozen=True)
class Detection:
    x: int
    y: int
    w: int
    h: int
    score: float | None


class FaceDetector:
    """
    Minimal wrapper around MediaPipe Face Detection.
    Returns an axis-aligned bounding box in pixel coordinates for a single face.
    """

    def __init__(self) -> None:
        self._mp = mp.solutions.face_detection
        self._detector = self._mp.FaceDetection(model_selection=0, min_detection_confidence=0.5)

    def detect_one(self, rgb_image, width: int, height: int) -> Detection | None:
        # MediaPipe expects RGB input.
        results = self._detector.process(rgb_image)
        if not results.detections:
            return None

        # Single-face assumption: pick the highest score.
        best = None
        best_score = -1.0
        for d in results.detections:
            score = None
            if d.score:
                score = float(d.score[0])
            if score is None:
                score = 0.0
            if score > best_score:
                best = d
                best_score = score

        if best is None:
            return None

        rbb = best.location_data.relative_bounding_box
        x = int(rbb.xmin * width)
        y = int(rbb.ymin * height)
        w = int(rbb.width * width)
        h = int(rbb.height * height)

        # Clamp to frame bounds, keep non-negative.
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        w = max(1, min(w, width - x))
        h = max(1, min(h, height - y))

        return Detection(x=x, y=y, w=w, h=h, score=best_score)

