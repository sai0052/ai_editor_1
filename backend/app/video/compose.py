from __future__ import annotations

from pathlib import Path

from app.video.ffmpeg import audio_encode_args, run_ffmpeg, video_encode_args


def concat_segments_fast(
    video_path: Path,
    output_path: Path,
    segments: list[tuple[float, float]],
    *,
    quality: str = "high",
    audio_filter: str | None = None,
    video_filter: str | None = None,
) -> Path:
    """
    Cut + join keep-segments in a single FFmpeg process.
    Concat pads must be interleaved: [v0][a0][v1][a1]...
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not segments:
        raise ValueError("No segments to concat")

    # Safer path when also applying heavy video filters:
    # 1) cut/join only  2) apply filters on the short result
    if video_filter or audio_filter:
        cut_only = output_path.with_name(output_path.stem + "_cut.mp4")
        _concat_only(video_path, cut_only, segments, quality=quality)
        return render_once(
            cut_only,
            output_path,
            quality=quality,
            video_filter=video_filter,
            audio_filter=audio_filter,
        )

    return _concat_only(video_path, output_path, segments, quality=quality)


def _concat_only(
    video_path: Path,
    output_path: Path,
    segments: list[tuple[float, float]],
    *,
    quality: str = "high",
) -> Path:
    fc_parts: list[str] = []
    pairs: list[str] = []
    for i, (start, end) in enumerate(segments):
        dur = max(0.05, end - start)
        fc_parts.append(
            f"[0:v]trim=start={start:.3f}:duration={dur:.3f},setpts=PTS-STARTPTS[v{i}]"
        )
        fc_parts.append(
            f"[0:a]atrim=start={start:.3f}:duration={dur:.3f},asetpts=PTS-STARTPTS[a{i}]"
        )
        pairs.append(f"[v{i}][a{i}]")

    n = len(segments)
    # CRITICAL: interleaved [v0][a0][v1][a1] — not all videos then all audios
    fc_parts.append(f"{''.join(pairs)}concat=n={n}:v=1:a=1[vcat][acat]")
    filter_complex = ";".join(fc_parts)

    run_ffmpeg(
        [
            "-i",
            str(video_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vcat]",
            "-map",
            "[acat]",
            *video_encode_args(quality),
            *audio_encode_args(),
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    return output_path


def render_once(
    video_path: Path,
    output_path: Path,
    *,
    quality: str = "high",
    video_filter: str | None = None,
    audio_filter: str | None = None,
) -> Path:
    """Single-pass render. Copies untouched streams when filters are absent."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    args: list[str] = ["-i", str(video_path)]

    if video_filter:
        args.extend(["-vf", video_filter, *video_encode_args(quality)])
    else:
        args.extend(["-c:v", "copy"])

    if audio_filter:
        args.extend(["-af", audio_filter, *audio_encode_args()])
    else:
        args.extend(["-c:a", "copy"])

    args.extend(["-movflags", "+faststart", str(output_path)])

    try:
        run_ffmpeg(args)
    except Exception:
        # Some containers refuse audio copy after video filter — re-encode audio
        if video_filter and not audio_filter:
            args = [
                "-i",
                str(video_path),
                "-vf",
                video_filter,
                *video_encode_args(quality),
                *audio_encode_args(),
                "-movflags",
                "+faststart",
                str(output_path),
            ]
            run_ffmpeg(args)
        else:
            raise
    return output_path
