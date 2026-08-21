from __future__ import annotations

import json
import shutil
from pathlib import Path

from app.config import Settings, get_settings
from app.models.schemas import VideoMetadata
from app.utils.security import new_id, safe_path_join


class StorageService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.settings.ensure_dirs()

    def create_video_dir(self, video_id: str | None = None) -> tuple[str, Path]:
        video_id = video_id or new_id("vid_")
        path = safe_path_join(self.settings.uploads_dir, video_id)
        path.mkdir(parents=True, exist_ok=True)
        return video_id, path

    def video_path(self, video_id: str, filename: str = "source") -> Path:
        folder = safe_path_join(self.settings.uploads_dir, video_id)
        # Find source file
        if filename != "source":
            return safe_path_join(folder, filename)
        for p in folder.glob("source.*"):
            return p
        meta = folder / "meta.json"
        if meta.exists():
            data = json.loads(meta.read_text(encoding="utf-8"))
            name = data.get("stored_name")
            if name:
                return safe_path_join(folder, name)
        raise FileNotFoundError(video_id)

    def save_metadata(self, video_id: str, metadata: VideoMetadata, stored_name: str) -> None:
        folder = safe_path_join(self.settings.uploads_dir, video_id)
        payload = metadata.model_dump()
        payload["stored_name"] = stored_name
        (folder / "meta.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load_metadata(self, video_id: str) -> VideoMetadata:
        folder = safe_path_join(self.settings.uploads_dir, video_id)
        meta_path = folder / "meta.json"
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        data.pop("stored_name", None)
        return VideoMetadata(**data)

    def create_job_dir(self, job_id: str | None = None) -> tuple[str, Path]:
        job_id = job_id or new_id("job_")
        path = safe_path_join(self.settings.jobs_dir, job_id)
        path.mkdir(parents=True, exist_ok=True)
        (path / "tmp").mkdir(exist_ok=True)
        return job_id, path

    def cleanup_job_temp(self, job_dir: Path) -> None:
        tmp = job_dir / "tmp"
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)

    def cleanup_path(self, path: Path) -> None:
        if path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
