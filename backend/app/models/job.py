from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.models.schemas import (
    EditOptions,
    EditSummary,
    ExportOptions,
    JobStatus,
    StageProgress,
    VideoMetadata,
    utcnow,
)


@dataclass
class JobRecord:
    job_id: str
    video_id: str
    status: JobStatus
    options: EditOptions
    export: ExportOptions
    metadata: VideoMetadata
    progress: float = 0.0
    stages: list[StageProgress] = field(default_factory=list)
    eta_seconds: float | None = None
    error: str | None = None
    summary: EditSummary | None = None
    original_path: str = ""
    result_path: str | None = None
    work_dir: str = ""
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    extras: dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = utcnow()
