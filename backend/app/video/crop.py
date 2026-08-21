from __future__ import annotations

from pathlib import Path

from app.video.ffmpeg import audio_encode_args, run_ffmpeg, video_encode_args

ASPECT_SIZES = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
}


def reframe_filter(aspect: str = "9:16") -> str:
    tw, th = ASPECT_SIZES.get(aspect, ASPECT_SIZES["9:16"])
    return f"scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th}"


def reframe_center(video_path: Path, output_path: Path, aspect: str = "9:16", quality: str = "high") -> Path:
    """
    Center-crop reframe toward target aspect.
    Subject detection hook lives in ai.subject — MVP uses geometric center crop.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    vf = reframe_filter(aspect)
    run_ffmpeg(
        [
            "-i",
            str(video_path),
            "-vf",
            vf,
            *video_encode_args(quality),
            *audio_encode_args(),
            str(output_path),
        ]
    )
    return output_path
