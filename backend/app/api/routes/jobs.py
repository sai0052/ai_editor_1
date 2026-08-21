from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.models.schemas import JobCreateRequest, JobResponse
from app.services.job_manager import enqueue_job, job_manager
from app.services.pipeline import build_stages
from app.services.storage import StorageService
from app.utils.errors import JobNotFoundError, VideoNotFoundError
from app.utils.security import new_id
from app.workers.processor import process_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse)
async def create_job(body: JobCreateRequest) -> JobResponse:
    storage = StorageService()
    try:
        metadata = storage.load_metadata(body.video_id)
        original = storage.video_path(body.video_id)
    except Exception as exc:
        raise VideoNotFoundError() from exc

    # Require at least one operation
    opts = body.options
    enabled = any(
        [
            opts.noise.enabled,
            opts.silence.enabled,
            opts.captions.enabled,
            opts.color.enabled,
            opts.pauses.enabled,
            opts.reframe.enabled,
            opts.jump_cuts.enabled,
            opts.filler.enabled,
        ]
    )
    if not enabled:
        from app.utils.errors import AppError

        raise AppError("Select at least one editing operation.", code="no_operations")

    job_id, work_dir = storage.create_job_dir(new_id("job_"))
    stages = build_stages(body.options)
    record = await job_manager.create(
        job_id=job_id,
        video_id=body.video_id,
        options=body.options,
        export=body.export,
        metadata=metadata,
        original_path=str(original),
        work_dir=str(work_dir),
        stages=stages,
    )
    await enqueue_job(job_id, process_job)
    return job_manager.to_response(record)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    try:
        job = job_manager.get(job_id)
    except JobNotFoundError:
        raise
    return job_manager.to_response(job)


@router.get("/{job_id}/result")
async def get_result(job_id: str):
    job = job_manager.get(job_id)
    if not job.result_path or not Path(job.result_path).exists():
        raise JobNotFoundError("Edited video is not ready yet.")
    return FileResponse(job.result_path, media_type="video/mp4", filename="autocut-export.mp4")
