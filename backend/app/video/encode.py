from __future__ import annotations

import shutil
from pathlib import Path

from app.models.schemas import ExportOptions, ExportQuality, ExportResolution
from app.video.ffmpeg import audio_encode_args, run_ffmpeg, video_encode_args


RESOLUTION_MAP = {
    ExportResolution.p1080: 1080,
    ExportResolution.p720: 720,
}


def export_needs_reencode(options: ExportOptions, src_height: int | None = None) -> bool:
    if options.fps != "original":
        return True
    if options.resolution == ExportResolution.original:
        return False
    target_h = RESOLUTION_MAP[options.resolution]
    if src_height and src_height <= target_h:
        return False
    return True


def export_video(source: Path, destination: Path, options: ExportOptions, src_height: int | None = None) -> Path:
    """Export final file. Stream-copies when resolution/fps are unchanged (huge speed win)."""
    destination.parent.mkdir(parents=True, exist_ok=True)

    if not export_needs_reencode(options, src_height):
        if source.resolve() == destination.resolve():
            return destination
        shutil.copy2(source, destination)
        return destination

    args: list[str] = ["-i", str(source)]
    vf_parts: list[str] = []
    if options.resolution != ExportResolution.original:
        target_h = RESOLUTION_MAP[options.resolution]
        if not (src_height and src_height <= target_h):
            vf_parts.append(f"scale=-2:{target_h}")

    if vf_parts:
        args.extend(["-vf", ",".join(vf_parts)])

    quality = options.quality.value if isinstance(options.quality, ExportQuality) else str(options.quality)
    args.extend(video_encode_args(quality))

    if options.fps != "original":
        args.extend(["-r", str(options.fps)])

    args.extend([*audio_encode_args(), "-movflags", "+faststart", str(destination)])
    run_ffmpeg(args)
    return destination
