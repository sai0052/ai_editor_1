from __future__ import annotations

from app.ai.base import BoundingBox, SubjectDetector


class CenterSubjectDetector(SubjectDetector):
    """
    Placeholder subject detector.
    Replace with face/person detection (e.g. MediaPipe, YOLO) without changing callers.
    """

    def detect(self, video_path: str, sample_fps: float = 1.0) -> list[BoundingBox]:
        # Normalized full-frame box centered — callers may use for fallback framing.
        return [BoundingBox(x=0.25, y=0.1, w=0.5, h=0.8, confidence=0.1, label="center_fallback")]


# Hook for future implementation:
# class MediaPipeFaceDetector(SubjectDetector):
#     def detect(self, video_path: str, sample_fps: float = 1.0) -> list[BoundingBox]:
#         ...
