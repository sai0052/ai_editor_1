from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class WordSpan:
    word: str
    start: float
    end: float


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    words: list[WordSpan] = field(default_factory=list)


@dataclass
class Transcript:
    language: str
    segments: list[TranscriptSegment]
    full_text: str


@dataclass
class BoundingBox:
    x: float
    y: float
    w: float
    h: float
    confidence: float = 1.0
    label: str = "subject"


@dataclass
class FillerHit:
    word: str
    start: float
    end: float
    safe_to_remove: bool = True
    reason: str = ""


class TranscriptionProvider(ABC):
    """Swap-friendly speech-to-text interface."""

    name: str = "base"

    @abstractmethod
    def transcribe(self, audio_path: str, language: str | None = None) -> Transcript:
        raise NotImplementedError


class SilenceDetector(ABC):
    @abstractmethod
    def detect(self, audio_path: str) -> list[tuple[float, float]]:
        raise NotImplementedError


class FillerWordDetector(ABC):
    @abstractmethod
    def detect(self, transcript: Transcript) -> list[FillerHit]:
        raise NotImplementedError


class SubjectDetector(ABC):
    """Future: face/object tracking for smart reframe."""

    @abstractmethod
    def detect(self, video_path: str, sample_fps: float = 1.0) -> list[BoundingBox]:
        raise NotImplementedError
