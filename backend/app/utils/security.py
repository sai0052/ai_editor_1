from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import Settings
from app.utils.errors import FileTooLargeError, UnsupportedFormatError

SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def new_id(prefix: str = "") -> str:
    token = uuid.uuid4().hex
    return f"{prefix}{token}" if prefix else token


def sanitize_filename(name: str) -> str:
    base = Path(name).name
    cleaned = SAFE_NAME_RE.sub("_", base).strip("._")
    return cleaned[:180] or "video.mp4"


def validate_upload(file: UploadFile, settings: Settings, size_bytes: int | None = None) -> str:
    filename = sanitize_filename(file.filename or "video.mp4")
    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_extensions:
        raise UnsupportedFormatError(
            f"Unsupported format '{ext or 'unknown'}'. Allowed: {', '.join(sorted(settings.allowed_extensions))}"
        )
    content_type = (file.content_type or "").lower()
    if content_type and not any(content_type.startswith(p) for p in settings.allowed_mime_prefixes):
        # Some browsers send application/octet-stream — allow if extension is valid
        if content_type not in {"application/octet-stream", "binary/octet-stream"}:
            raise UnsupportedFormatError("Uploaded file does not look like a video.")
    if size_bytes is not None and size_bytes > settings.max_upload_bytes:
        raise FileTooLargeError(
            f"File is too large. Maximum size is {settings.max_upload_bytes // (1024 * 1024)} MB."
        )
    return filename


def safe_path_join(root: Path, *parts: str) -> Path:
    """Join paths and ensure the result stays under root."""
    candidate = root.joinpath(*parts).resolve()
    root_resolved = root.resolve()
    if root_resolved != candidate and root_resolved not in candidate.parents:
        raise ValueError("Invalid path")
    return candidate
