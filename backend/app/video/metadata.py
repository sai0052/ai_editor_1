from __future__ import annotations

from pathlib import Path

from app.models.schemas import VideoMetadata
from app.utils.errors import InvalidVideoError
from app.video.ffmpeg import probe_json


def extract_metadata(path: Path, filename: str | None = None) -> VideoMetadata:
    data = probe_json(path)
    streams = data.get("streams") or []
    fmt = data.get("format") or {}

    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not video:
        raise InvalidVideoError("No video stream found in this file.")

    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    if width <= 0 or height <= 0:
        raise InvalidVideoError("Could not determine video resolution.")

    fps = _parse_fps(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1")
    duration = float(fmt.get("duration") or video.get("duration") or 0)
    size_bytes = int(fmt.get("size") or path.stat().st_size)

    return VideoMetadata(
        filename=filename or path.name,
        duration=duration,
        width=width,
        height=height,
        fps=fps,
        size_bytes=size_bytes,
        has_audio=audio is not None,
        codec=video.get("codec_name"),
        audio_codec=(audio or {}).get("codec_name"),
    )


def _parse_fps(rate: str) -> float:
    try:
        if "/" in rate:
            num, den = rate.split("/", 1)
            den_f = float(den)
            return float(num) / den_f if den_f else 0.0
        return float(rate)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0
