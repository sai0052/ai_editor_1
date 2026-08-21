from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AutoCut"
    api_prefix: str = "/api"
    app_url: str = "https://ai-editor-1-1.onrender.com"
    cors_origins: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "https://aieditor.website,"
        "https://www.aieditor.website,"
        "https://ai-editor-1-1.onrender.com"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [item.strip().rstrip("/") for item in self.cors_origins.split(",") if item.strip()]
        primary = self.app_url.rstrip("/")
        if primary and primary not in origins:
            origins.append(primary)
        if primary.startswith("https://") and "://www." not in primary:
            www = primary.replace("https://", "https://www.", 1)
            if www not in origins:
                origins.append(www)
        return origins

    # Storage
    base_dir: Path = Path(__file__).resolve().parent.parent
    storage_dir: Path = base_dir / "storage"
    uploads_dir: Path = storage_dir / "uploads"
    jobs_dir: Path = storage_dir / "jobs"
    temp_dir: Path = storage_dir / "temp"

    # Limits
    max_upload_bytes: int = 2 * 1024 * 1024 * 1024  # 2 GB
    allowed_extensions: set[str] = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
    allowed_mime_prefixes: tuple[str, ...] = ("video/",)

    # Processing
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    job_timeout_seconds: int = 3600
    whisper_model: str = "base"
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    groq_whisper_model: str = "whisper-large-v3-turbo"
    transcription_provider: str = "auto"  # auto | groq | faster-whisper | openai | none

    def ensure_dirs(self) -> None:
        for path in (self.uploads_dir, self.jobs_dir, self.temp_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
