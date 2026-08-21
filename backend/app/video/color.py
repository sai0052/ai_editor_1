from __future__ import annotations

from pathlib import Path

from app.models.schemas import ColorOptions, ColorPreset
from app.video.ffmpeg import audio_encode_args, run_ffmpeg, video_encode_args

PRESET_EQ = {
    ColorPreset.natural: {"brightness": 0.02, "contrast": 1.05, "saturation": 1.05, "gamma": 1.0},
    ColorPreset.cinematic: {"brightness": -0.02, "contrast": 1.15, "saturation": 0.92, "gamma": 1.05},
    ColorPreset.warm: {"brightness": 0.03, "contrast": 1.08, "saturation": 1.12, "gamma": 1.0},
    ColorPreset.cool: {"brightness": 0.0, "contrast": 1.08, "saturation": 1.05, "gamma": 1.0},
    ColorPreset.vibrant: {"brightness": 0.04, "contrast": 1.2, "saturation": 1.35, "gamma": 0.98},
    ColorPreset.moody: {"brightness": -0.06, "contrast": 1.25, "saturation": 0.85, "gamma": 1.1},
    ColorPreset.high_contrast: {"brightness": 0.0, "contrast": 1.4, "saturation": 1.1, "gamma": 1.0},
    ColorPreset.auto: {"brightness": 0.03, "contrast": 1.12, "saturation": 1.1, "gamma": 1.0},
}


def _temperature_filter(temp: float) -> str | None:
    """temp -1..1 → colorbalance-ish rs/bs shift."""
    if abs(temp) < 0.01:
        return None
    warm = max(-1.0, min(1.0, temp))
    rs = 0.08 * warm
    bs = -0.08 * warm
    return f"colorbalance=rs={rs:.3f}:bs={bs:.3f}"


def build_color_filter(options: ColorOptions) -> str:
    preset = options.preset
    if options.auto_color:
        preset = ColorPreset.auto
    base = PRESET_EQ.get(preset, PRESET_EQ[ColorPreset.natural])

    brightness = base["brightness"] + options.brightness
    contrast = base["contrast"] * options.contrast
    saturation = base["saturation"] * options.saturation
    gamma = base["gamma"]

    # Map highlights/shadows roughly into gamma / brightness
    brightness += options.shadows * 0.05 - options.highlights * 0.03
    gamma += options.highlights * 0.05 - options.shadows * 0.04

    brightness = max(-1.0, min(1.0, brightness))
    contrast = max(0.2, min(3.0, contrast))
    saturation = max(0.0, min(3.0, saturation))
    gamma = max(0.1, min(10.0, gamma))

    filters = [f"eq=brightness={brightness:.3f}:contrast={contrast:.3f}:saturation={saturation:.3f}:gamma={gamma:.3f}"]
    temp = options.temperature
    if preset == ColorPreset.warm and abs(temp) < 0.01:
        temp = 0.35
    elif preset == ColorPreset.cool and abs(temp) < 0.01:
        temp = -0.35
    elif preset == ColorPreset.cinematic and abs(temp) < 0.01:
        temp = -0.1
    tf = _temperature_filter(temp)
    if tf:
        filters.append(tf)
    return ",".join(filters)


def apply_color_grade(video_path: Path, output_path: Path, options: ColorOptions, quality: str = "high") -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    vf = build_color_filter(options)
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
