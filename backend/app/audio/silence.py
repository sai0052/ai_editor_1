from __future__ import annotations

import logging
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.models.schemas import SilencePreset
from app.video.compose import concat_segments_fast
from app.video.ffmpeg import run_ffmpeg

logger = logging.getLogger(__name__)


@dataclass
class SilenceInterval:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


# noise_db here is a *fallback* floor; adaptive detection usually overrides it.
# Higher (less negative) = treat more ambient audio as "silence" = more cuts.
PRESET_PARAMS = {
    SilencePreset.conservative: {"min_silence": 1.0, "keep": 0.28, "noise_db": -32, "rel_db": 18},
    SilencePreset.balanced: {"min_silence": 0.55, "keep": 0.15, "noise_db": -28, "rel_db": 16},
    SilencePreset.aggressive: {"min_silence": 0.35, "keep": 0.08, "noise_db": -24, "rel_db": 14},
}


def measure_volume(media_path: Path) -> tuple[float | None, float | None]:
    """Return (mean_volume_db, max_volume_db) via FFmpeg volumedetect."""
    null_sink = "NUL" if os.name == "nt" else "/dev/null"
    proc = run_ffmpeg(
        [
            "-i",
            str(media_path),
            "-vn",
            "-af",
            "volumedetect",
            "-f",
            "null",
            null_sink,
        ]
    )
    text = (proc.stderr or "") + (proc.stdout or "")
    mean = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", text)
    peak = re.search(r"max_volume:\s*([-\d.]+)\s*dB", text)
    mean_v = float(mean.group(1)) if mean else None
    peak_v = float(peak.group(1)) if peak else None
    return mean_v, peak_v


def adaptive_noise_threshold(
    media_path: Path,
    *,
    fallback_db: float = -28,
    rel_db: float = 16,
) -> float:
    """
    Pick a silence threshold from the clip's loudness.
    Quiet gaps with room tone are often louder than a fixed -35 dB gate.
    """
    mean_v, peak_v = measure_volume(media_path)
    candidates = [fallback_db]
    if peak_v is not None:
        candidates.append(peak_v - rel_db)
    if mean_v is not None:
        # A bit above the mean catches pauses that still have room tone
        candidates.append(mean_v + 4.0)
    # Clamp to a practical speech range
    threshold = max(candidates)
    threshold = max(-45.0, min(-18.0, threshold))
    logger.info(
        "silence threshold=%.1f dB (mean=%s peak=%s fallback=%.1f)",
        threshold,
        mean_v,
        peak_v,
        fallback_db,
    )
    return threshold


def detect_silences(
    media_path: Path,
    *,
    min_silence: float = 0.55,
    noise_db: float = -28,
    adaptive: bool = True,
    rel_db: float = 16,
    duration: float | None = None,
) -> list[SilenceInterval]:
    """Detect long quiet sections. Uses adaptive threshold by default."""
    threshold = (
        adaptive_noise_threshold(media_path, fallback_db=noise_db, rel_db=rel_db)
        if adaptive
        else noise_db
    )
    null_sink = "NUL" if os.name == "nt" else "/dev/null"
    proc = run_ffmpeg(
        [
            "-i",
            str(media_path),
            "-vn",
            "-af",
            f"silencedetect=noise={threshold:.1f}dB:d={min_silence}",
            "-f",
            "null",
            null_sink,
        ]
    )
    text = (proc.stderr or "") + (proc.stdout or "")
    starts = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", text)]
    # silence_end may include "| silence_duration: N"
    ends = [float(x) for x in re.findall(r"silence_end:\s*([0-9.]+)", text)]

    intervals: list[SilenceInterval] = []
    for i, start in enumerate(starts):
        if i < len(ends):
            end = ends[i]
        elif duration is not None:
            end = duration
        else:
            continue
        if end - start >= min_silence - 1e-3:
            intervals.append(SilenceInterval(start=start, end=end))

    # If adaptive found nothing, retry once with a more permissive gate
    if not intervals and adaptive and threshold > -32:
        return detect_silences(
            media_path,
            min_silence=min_silence,
            noise_db=min(-22.0, threshold + 6),
            adaptive=False,
            duration=duration,
        )

    return _merge_intervals(intervals)


def detect_silences_from_transcript_gaps(
    segments: list[tuple[float, float]],
    *,
    duration: float,
    min_silence: float = 0.55,
) -> list[SilenceInterval]:
    """
    Treat gaps between speech cues as silence.
    Reliable when room tone fools pure energy detection.
    """
    if not segments:
        return []
    ordered = sorted((float(s), float(e)) for s, e in segments if e > s)
    gaps: list[SilenceInterval] = []
    # Leading silence
    if ordered[0][0] >= min_silence:
        gaps.append(SilenceInterval(0.0, ordered[0][0]))
    for ( _s1, e1), (s2, _e2) in zip(ordered, ordered[1:]):
        gap = s2 - e1
        if gap >= min_silence:
            gaps.append(SilenceInterval(e1, s2))
    # Trailing silence
    if duration - ordered[-1][1] >= min_silence:
        gaps.append(SilenceInterval(ordered[-1][1], duration))
    return _merge_intervals(gaps)


def merge_silence_lists(*lists: list[SilenceInterval]) -> list[SilenceInterval]:
    all_items: list[SilenceInterval] = []
    for lst in lists:
        all_items.extend(lst)
    return _merge_intervals(all_items)


def _merge_intervals(intervals: list[SilenceInterval]) -> list[SilenceInterval]:
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda x: x.start)
    merged: list[SilenceInterval] = [ordered[0]]
    for item in ordered[1:]:
        prev = merged[-1]
        if item.start <= prev.end + 0.05:
            merged[-1] = SilenceInterval(prev.start, max(prev.end, item.end))
        else:
            merged.append(item)
    return merged


def build_keep_segments(
    duration: float,
    silences: list[SilenceInterval],
    keep_silence: float,
) -> list[tuple[float, float]]:
    """Convert silence intervals into keep segments, retaining a small pad."""
    if duration <= 0:
        return []
    if not silences:
        return [(0.0, duration)]

    keep: list[tuple[float, float]] = []
    cursor = 0.0
    # Keep a small natural pause at each side of a cut
    pad = max(0.0, keep_silence)

    for silence in silences:
        # Remove the middle of the silence; leave `pad` total (split sides)
        left_pad = pad / 2.0
        right_pad = pad / 2.0
        cut_start = silence.start + left_pad
        cut_end = silence.end - right_pad
        if cut_end <= cut_start + 0.05:
            # Silence barely longer than pad — still collapse it to a tiny pause
            mid = (silence.start + silence.end) / 2.0
            half_keep = min(0.04, silence.duration / 4.0)
            cut_start = mid - half_keep
            cut_end = mid + half_keep
        if cut_start > cursor + 0.04:
            keep.append((cursor, cut_start))
        cursor = max(cursor, cut_end)

    if cursor < duration - 0.04:
        keep.append((cursor, duration))

    merged: list[tuple[float, float]] = []
    for start, end in keep:
        if end - start < 0.04:
            continue
        if merged and start - merged[-1][1] < 0.02:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))

    # Guard: never return empty
    if not merged:
        return [(0.0, duration)]

    # Guard: if we barely removed anything (<80ms total), treat as no-op
    kept = sum(e - s for s, e in merged)
    if kept >= duration - 0.08:
        return [(0.0, duration)]

    return merged


def remove_silences(
    video_path: Path,
    output_path: Path,
    duration: float,
    *,
    preset: SilencePreset = SilencePreset.balanced,
    min_silence_ms: int | None = None,
    keep_silence_ms: int | None = None,
    quality: str = "high",
    video_filter: str | None = None,
    audio_filter: str | None = None,
) -> tuple[Path, int, list[tuple[float, float]] | None]:
    params = PRESET_PARAMS[preset]
    min_silence = (min_silence_ms / 1000.0) if min_silence_ms is not None else params["min_silence"]
    keep_silence = (keep_silence_ms / 1000.0) if keep_silence_ms is not None else params["keep"]

    silences = detect_silences(
        video_path,
        min_silence=min_silence,
        noise_db=params["noise_db"],
        adaptive=True,
        rel_db=params["rel_db"],
        duration=duration,
    )
    if not silences:
        if video_filter or audio_filter:
            from app.video.compose import render_once

            render_once(
                video_path,
                output_path,
                quality=quality,
                video_filter=video_filter,
                audio_filter=audio_filter,
            )
        else:
            shutil.copy2(video_path, output_path)
        return output_path, 0, None

    segments = build_keep_segments(duration, silences, keep_silence)
    if len(segments) == 1 and abs(segments[0][0]) < 0.01 and abs(segments[0][1] - duration) < 0.05:
        if video_filter or audio_filter:
            from app.video.compose import render_once

            render_once(
                video_path,
                output_path,
                quality=quality,
                video_filter=video_filter,
                audio_filter=audio_filter,
            )
        else:
            shutil.copy2(video_path, output_path)
        return output_path, 0, segments

    concat_segments_fast(
        video_path,
        output_path,
        segments,
        quality=quality,
        video_filter=video_filter,
        audio_filter=audio_filter,
    )
    return output_path, len(silences), segments


def _concat_segments(
    video_path: Path,
    output_path: Path,
    segments: list[tuple[float, float]],
    quality: str = "high",
) -> Path:
    return concat_segments_fast(video_path, output_path, segments, quality=quality)
