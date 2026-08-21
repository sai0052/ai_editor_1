from __future__ import annotations

from app.services.pipeline import EditPipeline


async def process_job(job_id: str) -> None:
    pipeline = EditPipeline()
    await pipeline.run(job_id)
