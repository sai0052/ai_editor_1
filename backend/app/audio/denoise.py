from __future__ import annotations

from pathlib import Path

from app.models.schemas import NoiseStrength
from app.video.ffmpeg import run_ffmpeg


STRENGTH_MAP = {
    NoiseStrength.low: {"nf": -18, "nr": 6},
    NoiseStrength.medium: {"nf": -25, "nr": 10},
    NoiseStrength.high: {"nf": -32, "nr": 16},
}


def denoise_filter(strength: NoiseStrength = NoiseStrength.medium) -> str:
    """Lightweight voice-preserving denoise chain (no slow loudnorm 2-pass)."""
    params = STRENGTH_MAP.get(strength, STRENGTH_MAP[NoiseStrength.medium])
    return f"highpass=f=80,afftdn=nf={params['nf']}:nr={params['nr']}:tn=1"


def denoise_audio(
    input_audio: Path,
    output_audio: Path,
    strength: NoiseStrength = NoiseStrength.medium,
) -> Path:
    output_audio.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            "-i",
            str(input_audio),
            "-af",
            denoise_filter(strength),
            str(output_audio),
        ]
    )
    return output_audio


def denoise_video_audio(
    video_path: Path,
    output_path: Path,
    strength: NoiseStrength = NoiseStrength.medium,
    quality: str = "high",
) -> Path:
    """Denoise audio only — video stream is copied (no re-encode)."""
    from app.video.ffmpeg import audio_encode_args

    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            "-i",
            str(video_path),
            "-c:v",
            "copy",
            "-af",
            denoise_filter(strength),
            *audio_encode_args(),
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    return output_path
