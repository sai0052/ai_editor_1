from __future__ import annotations

from pathlib import Path

from app.video.ffmpeg import audio_encode_args, run_ffmpeg, video_encode_args


def extract_audio(video_path: Path, output_wav: Path, sample_rate: int = 16000) -> Path:
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            str(output_wav),
        ]
    )
    return output_wav


def replace_audio(video_path: Path, audio_path: Path, output_path: Path, quality: str = "high") -> Path:
    """Mux new audio onto video, stream-copy video when possible."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Prefer copy video to avoid re-encode
    try:
        run_ffmpeg(
            [
                "-i",
                str(video_path),
                "-i",
                str(audio_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                *audio_encode_args(),
                "-shortest",
                str(output_path),
            ]
        )
    except Exception:
        run_ffmpeg(
            [
                "-i",
                str(video_path),
                "-i",
                str(audio_path),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                *video_encode_args(quality),
                *audio_encode_args(),
                "-shortest",
                str(output_path),
            ]
        )
    return output_path
