from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    analyzing = "analyzing"
    processing = "processing"
    rendering = "rendering"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class NoiseStrength(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class SilencePreset(str, Enum):
    conservative = "conservative"
    balanced = "balanced"
    aggressive = "aggressive"


class CaptionStyle(str, Enum):
    clean = "clean"
    bold = "bold"
    modern = "modern"
    minimal = "minimal"
    social = "social"
    highlighted = "highlighted"


class ColorPreset(str, Enum):
    natural = "natural"
    cinematic = "cinematic"
    warm = "warm"
    cool = "cool"
    vibrant = "vibrant"
    moody = "moody"
    high_contrast = "high_contrast"
    auto = "auto"


class FillerMode(str, Enum):
    keep = "keep"
    remove = "remove"
    review = "review"


class AspectRatio(str, Enum):
    landscape = "16:9"
    portrait = "9:16"
    square = "1:1"


class ExportResolution(str, Enum):
    original = "original"
    p1080 = "1080p"
    p720 = "720p"


class ExportQuality(str, Enum):
    standard = "standard"
    high = "high"
    maximum = "maximum"


class NoiseOptions(BaseModel):
    enabled: bool = False
    strength: NoiseStrength = NoiseStrength.medium


class SilenceOptions(BaseModel):
    enabled: bool = False
    preset: SilencePreset = SilencePreset.balanced
    min_silence_ms: int | None = None
    keep_silence_ms: int | None = None


class CaptionOptions(BaseModel):
    enabled: bool = False
    language: str = "auto"
    style: CaptionStyle = CaptionStyle.clean
    font: str = "Arial"
    font_size: int = 48
    position: Literal["bottom", "center", "top"] = "bottom"
    color: str = "#FFFFFF"
    background: str = "#000000AA"
    stroke: str = "#000000"
    highlight_color: str = "#FFD166"
    burn_in: bool = True


class ColorOptions(BaseModel):
    enabled: bool = False
    preset: ColorPreset = ColorPreset.natural
    auto_color: bool = False
    brightness: float = 0.0  # -1..1
    contrast: float = 1.0  # 0..2
    saturation: float = 1.0  # 0..3
    highlights: float = 0.0
    shadows: float = 0.0
    temperature: float = 0.0  # -1 cool .. 1 warm


class PauseOptions(BaseModel):
    enabled: bool = False
    aggressiveness: float = 0.5


class ReframeOptions(BaseModel):
    enabled: bool = False
    aspect: AspectRatio = AspectRatio.portrait


class JumpCutOptions(BaseModel):
    enabled: bool = False
    aggressiveness: float = 0.4


class FillerOptions(BaseModel):
    enabled: bool = False
    mode: FillerMode = FillerMode.remove


class EditOptions(BaseModel):
    noise: NoiseOptions = Field(default_factory=NoiseOptions)
    silence: SilenceOptions = Field(default_factory=SilenceOptions)
    captions: CaptionOptions = Field(default_factory=CaptionOptions)
    color: ColorOptions = Field(default_factory=ColorOptions)
    pauses: PauseOptions = Field(default_factory=PauseOptions)
    reframe: ReframeOptions = Field(default_factory=ReframeOptions)
    jump_cuts: JumpCutOptions = Field(default_factory=JumpCutOptions)
    filler: FillerOptions = Field(default_factory=FillerOptions)


class ExportOptions(BaseModel):
    resolution: ExportResolution = ExportResolution.original
    format: Literal["mp4"] = "mp4"
    fps: Literal["original", "24", "30", "60"] = "original"
    quality: ExportQuality = ExportQuality.high


class VideoMetadata(BaseModel):
    filename: str
    duration: float
    width: int
    height: int
    fps: float
    size_bytes: int
    has_audio: bool
    codec: str | None = None
    audio_codec: str | None = None


class StageProgress(BaseModel):
    id: str
    label: str
    status: Literal["pending", "running", "completed", "skipped", "failed"] = "pending"
    detail: str | None = None
    progress: float = 0.0


class EditSummary(BaseModel):
    noise_reduced: bool = False
    silences_removed: int = 0
    captions_generated: bool = False
    color_applied: bool = False
    filler_removed: int = 0
    jump_cuts: int = 0
    reframed: bool = False
    pauses_shortened: int = 0
    notes: list[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    video_id: str
    metadata: VideoMetadata


class JobCreateRequest(BaseModel):
    video_id: str
    options: EditOptions
    export: ExportOptions = Field(default_factory=ExportOptions)


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: float = 0.0
    stages: list[StageProgress] = Field(default_factory=list)
    eta_seconds: float | None = None
    error: str | None = None
    summary: EditSummary | None = None
    original_url: str | None = None
    result_url: str | None = None
    created_at: datetime
    updated_at: datetime
    options: EditOptions | None = None


class ErrorResponse(BaseModel):
    error: str
    code: str
    details: dict[str, Any] | None = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
