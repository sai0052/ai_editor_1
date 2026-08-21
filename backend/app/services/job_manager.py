from __future__ import annotations

import asyncio
import logging
from typing import Callable, Awaitable

from app.models.job import JobRecord
from app.models.schemas import (
    EditOptions,
    EditSummary,
    ExportOptions,
    JobResponse,
    JobStatus,
    StageProgress,
    VideoMetadata,
)
from app.utils.errors import JobNotFoundError

logger = logging.getLogger(__name__)


class JobManager:
    """In-memory job registry. Swap for Redis/DB later without changing API routes."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        job_id: str,
        video_id: str,
        options: EditOptions,
        export: ExportOptions,
        metadata: VideoMetadata,
        original_path: str,
        work_dir: str,
        stages: list[StageProgress],
    ) -> JobRecord:
        record = JobRecord(
            job_id=job_id,
            video_id=video_id,
            status=JobStatus.queued,
            options=options,
            export=export,
            metadata=metadata,
            stages=stages,
            original_path=original_path,
            work_dir=work_dir,
        )
        async with self._lock:
            self._jobs[job_id] = record
        return record

    def get(self, job_id: str) -> JobRecord:
        job = self._jobs.get(job_id)
        if not job:
            raise JobNotFoundError()
        return job

    def to_response(self, job: JobRecord) -> JobResponse:
        return JobResponse(
            job_id=job.job_id,
            status=job.status,
            progress=job.progress,
            stages=job.stages,
            eta_seconds=job.eta_seconds,
            error=job.error,
            summary=job.summary,
            original_url=f"/api/videos/{job.video_id}/file",
            result_url=f"/api/jobs/{job.job_id}/result" if job.result_path else None,
            created_at=job.created_at,
            updated_at=job.updated_at,
            options=job.options,
        )

    async def update(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        progress: float | None = None,
        stages: list[StageProgress] | None = None,
        eta_seconds: float | None = None,
        error: str | None = None,
        summary: EditSummary | None = None,
        result_path: str | None = None,
    ) -> JobRecord:
        async with self._lock:
            job = self.get(job_id)
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = max(0.0, min(100.0, progress))
            if stages is not None:
                job.stages = stages
            if eta_seconds is not None:
                job.eta_seconds = eta_seconds
            if error is not None:
                job.error = error
            if summary is not None:
                job.summary = summary
            if result_path is not None:
                job.result_path = result_path
            job.touch()
            return job

    async def set_stage(
        self,
        job_id: str,
        stage_id: str,
        status: str,
        detail: str | None = None,
        progress: float | None = None,
    ) -> None:
        async with self._lock:
            job = self.get(job_id)
            for stage in job.stages:
                if stage.id == stage_id:
                    stage.status = status  # type: ignore[assignment]
                    if detail is not None:
                        stage.detail = detail
                    if progress is not None:
                        stage.progress = progress
                    break
            completed = sum(1 for s in job.stages if s.status in ("completed", "skipped"))
            total = max(1, len(job.stages))
            job.progress = (completed / total) * 100.0
            if any(s.status == "running" for s in job.stages):
                running = next(s for s in job.stages if s.status == "running")
                idx = job.stages.index(running)
                job.progress = ((idx + running.progress / 100.0) / total) * 100.0
            job.touch()


job_manager = JobManager()


async def enqueue_job(job_id: str, runner: Callable[[str], Awaitable[None]]) -> None:
    asyncio.create_task(_safe_run(job_id, runner))


async def _safe_run(job_id: str, runner: Callable[[str], Awaitable[None]]) -> None:
    try:
        await runner(job_id)
    except Exception:
        logger.exception("Job %s crashed", job_id)
        try:
            await job_manager.update(
                job_id,
                status=JobStatus.failed,
                error="Processing failed unexpectedly. Please try again.",
            )
        except Exception:
            pass
