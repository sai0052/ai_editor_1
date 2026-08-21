"""Generate a clip with obvious silence and verify adaptive silence cutting."""
from pathlib import Path

from app.audio.silence import (
    SilencePreset,
    build_keep_segments,
    detect_silences,
    detect_silences_from_transcript_gaps,
    merge_silence_lists,
    remove_silences,
)
from app.video.ffmpeg import run_ffmpeg
from app.video.metadata import extract_metadata

tmp = Path("storage/temp")
tmp.mkdir(parents=True, exist_ok=True)
src = tmp / "silence_demo.mp4"

# 1s tone, 2s silence, 1s tone  => ~4s total, should remove ~2s
run_ffmpeg(
    [
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=1",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=mono",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=550:duration=1",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=640x360:d=4",
        "-filter_complex",
        "[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]",
        "-map",
        "3:v",
        "-map",
        "[a]",
        "-t",
        "4",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        str(src),
    ]
)

meta = extract_metadata(src)
print("duration", meta.duration)

silences = detect_silences(src, min_silence=0.5, noise_db=-28, adaptive=True, duration=meta.duration)
print("energy silences", [(round(s.start, 2), round(s.end, 2), round(s.duration, 2)) for s in silences])

gaps = detect_silences_from_transcript_gaps([(0.0, 1.0), (3.0, 4.0)], duration=meta.duration, min_silence=0.5)
print("transcript gaps", [(round(s.start, 2), round(s.end, 2)) for s in gaps])

combined = merge_silence_lists(silences, gaps)
keep = build_keep_segments(meta.duration, combined, keep_silence=0.15)
print("keep", [(round(s, 2), round(e, 2)) for s, e in keep], "kept_sec", round(sum(e - s for s, e in keep), 2))

out = tmp / "silence_demo_out.mp4"
path, n, segs = remove_silences(src, out, meta.duration, preset=SilencePreset.balanced)
out_meta = extract_metadata(out)
print("removed_count", n, "out_duration", round(out_meta.duration, 2), "ok", out_meta.duration < meta.duration - 0.5)
