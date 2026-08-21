from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from app.config import get_settings
from app.utils.errors import FFmpegError

logger = logging.getLogger(__name__)


def _bin(name: str) -> str:
    settings = get_settings()
    configured = settings.ffmpeg_bin if name == "ffmpeg" else settings.ffprobe_bin
    found = shutil.which(configured) or shutil.which(name)
    if not found:
        raise FFmpegError(f"{name} is not installed or not on PATH.")
    return found


def run_ffmpeg(args: Sequence[str], *, timeout: int | None = None, progress_callback=None) -> subprocess.CompletedProcess[str]:
    """Run FFmpeg with a safe argument list (never shell=True)."""
    cmd = [_bin("ffmpeg"), "-hide_banner", "-y", *args]
    logger.info("ffmpeg %s", " ".join(cmd[1:]))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout or get_settings().job_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError("Video processing timed out. Try a shorter clip or fewer options.") from exc
    if proc.returncode != 0:
        stderr = (proc.stderr or "")[-2500:]
        logger.error("ffmpeg failed: %s", stderr)
        raise FFmpegError(_friendly_ffmpeg_message(stderr), details={"stderr_tail": stderr})
    return proc


def _friendly_ffmpeg_message(stderr: str) -> str:
    low = (stderr or "").lower()
    if "error linking filters" in low or "media type mismatch" in low:
        return "Editing filters could not be combined for this clip. Retrying with a safer path — please try again."
    if "no such filter" in low and "ass" in low:
        return "Caption burn-in is unavailable in this FFmpeg build. Captions file was still saved."
    if "unknown encoder" in low or "encoder not found" in low:
        return "Required video encoder is missing from FFmpeg on this machine."
    if "invalid data found" in low or "moov atom not found" in low:
        return "This video file looks corrupted or incomplete."
    if "does not contain any stream" in low:
        return "No usable video/audio streams were found in this file."
    if "permission denied" in low:
        return "Could not write the output file. Check disk permissions and free space."
    if "no space left" in low:
        return "Not enough disk space to finish rendering."
    return "Video processing hit a technical error. Try fewer options or a different export quality."


async def run_ffmpeg_async(args: Sequence[str], *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return await asyncio.to_thread(run_ffmpeg, args, timeout=timeout)


def run_ffprobe(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    cmd = [_bin("ffprobe"), *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError("Could not read video metadata.") from exc
    if proc.returncode != 0:
        raise FFmpegError("Could not read this video. It may be corrupted.")
    return proc


def probe_json(path: Path) -> dict:
    proc = run_ffprobe(
        [
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise FFmpegError("Could not parse video metadata.") from exc


_nvenc_usable: bool | None = None


def has_nvenc() -> bool:
    """True only if h264_nvenc can actually open (CUDA present), not merely listed."""
    global _nvenc_usable
    if _nvenc_usable is not None:
        return _nvenc_usable
    import os

    null_sink = "NUL" if os.name == "nt" else "/dev/null"
    try:
        proc = subprocess.run(
            [
                _bin("ffmpeg"),
                "-hide_banner",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=64x64:d=0.1",
                "-frames:v",
                "1",
                "-c:v",
                "h264_nvenc",
                "-f",
                "null",
                null_sink,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        _nvenc_usable = proc.returncode == 0
    except Exception:
        _nvenc_usable = False
    return _nvenc_usable


def video_encode_args(quality: str = "high", prefer_hw: bool = True) -> list[str]:
    """
    Fast-first encoder args.
    Editing prioritizes turnaround time; 'maximum' still stays reasonably quick.
    """
    # Faster presets than typical archival encodes
    crf = {"standard": "28", "high": "23", "maximum": "20"}.get(quality, "23")
    preset = {"standard": "ultrafast", "high": "veryfast", "maximum": "veryfast"}.get(quality, "veryfast")
    if prefer_hw and has_nvenc():
        cq = {"standard": "28", "high": "24", "maximum": "21"}.get(quality, "24")
        return [
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p1",  # fastest NVENC preset
            "-rc",
            "vbr",
            "-cq",
            cq,
            "-b:v",
            "0",
            "-spatial_aq",
            "0",
        ]
    return [
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        crf,
        "-pix_fmt",
        "yuv420p",
        "-threads",
        "0",
    ]


def audio_encode_args() -> list[str]:
    # Slightly lower bitrate = faster AAC encode, still fine for speech
    return ["-c:a", "aac", "-b:a", "160k", "-ac", "2"]
