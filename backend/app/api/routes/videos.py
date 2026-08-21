from __future__ import annotations

import aiofiles
from fastapi import APIRouter, File, UploadFile

from app.config import get_settings
from app.models.schemas import UploadResponse
from app.services.storage import StorageService
from app.utils.errors import FileTooLargeError, InvalidVideoError, VideoNotFoundError
from app.utils.security import new_id, validate_upload
from app.video.metadata import extract_metadata
from fastapi.responses import FileResponse

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)) -> UploadResponse:
    settings = get_settings()
    storage = StorageService(settings)

    # Stream to disk with size guard
    video_id, folder = storage.create_video_dir(new_id("vid_"))
    filename = validate_upload(file, settings)
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ".mp4"
    stored_name = f"source{ext}"
    dest = folder / stored_name

    size = 0
    chunk_size = 1024 * 1024
    try:
        async with aiofiles.open(dest, "wb") as out:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    await out.close()
                    storage.cleanup_path(folder)
                    raise FileTooLargeError(
                        f"File is too large. Maximum size is {settings.max_upload_bytes // (1024 * 1024)} MB."
                    )
                await out.write(chunk)
    finally:
        await file.close()

    if size == 0:
        storage.cleanup_path(folder)
        raise InvalidVideoError("Uploaded file is empty.")

    try:
        metadata = extract_metadata(dest, filename=filename)
    except Exception:
        storage.cleanup_path(folder)
        raise

    storage.save_metadata(video_id, metadata, stored_name)
    return UploadResponse(video_id=video_id, metadata=metadata)


@router.get("/{video_id}")
async def get_video_meta(video_id: str):
    storage = StorageService()
    try:
        meta = storage.load_metadata(video_id)
    except Exception as exc:
        raise VideoNotFoundError() from exc
    return {"video_id": video_id, "metadata": meta}


@router.get("/{video_id}/file")
async def get_video_file(video_id: str):
    storage = StorageService()
    try:
        path = storage.video_path(video_id)
    except Exception as exc:
        raise VideoNotFoundError() from exc
    return FileResponse(path, media_type="video/mp4", filename=path.name)
