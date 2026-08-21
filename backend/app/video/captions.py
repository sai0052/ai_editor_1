from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.models.schemas import CaptionOptions, CaptionStyle
from app.video.ffmpeg import audio_encode_args, run_ffmpeg, video_encode_args


@dataclass
class WordTiming:
    word: str
    start: float
    end: float


@dataclass
class CaptionSegment:
    start: float
    end: float
    text: str
    words: list[WordTiming] | None = None


STYLE_PRESETS = {
    CaptionStyle.clean: {"fontsize_mul": 1.0, "bold": 0, "outline": 2, "shadow": 0},
    CaptionStyle.bold: {"fontsize_mul": 1.15, "bold": 1, "outline": 3, "shadow": 1},
    CaptionStyle.modern: {"fontsize_mul": 1.05, "bold": 1, "outline": 0, "shadow": 2},
    CaptionStyle.minimal: {"fontsize_mul": 0.9, "bold": 0, "outline": 1, "shadow": 0},
    CaptionStyle.social: {"fontsize_mul": 1.25, "bold": 1, "outline": 4, "shadow": 0},
    CaptionStyle.highlighted: {"fontsize_mul": 1.1, "bold": 1, "outline": 2, "shadow": 0},
}


def _ass_color(hex_color: str) -> str:
    """Convert #RRGGBB or #RRGGBBAA to ASS &HAABBGGRR."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = h[0:2], h[2:4], h[4:6]
        a = "00"
    elif len(h) == 8:
        r, g, b, a = h[0:2], h[2:4], h[4:6], h[6:8]
        # ASS alpha is inverted (00 opaque)
        a = f"{255 - int(a, 16):02X}"
    else:
        return "&H00FFFFFF"
    return f"&H{a}{b}{g}{r}".upper()


def _ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 0
        s += 1
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def segments_to_srt(segments: list[CaptionSegment]) -> str:
    lines: list[str] = []
    for i, seg in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{_srt_ts(seg.start)} --> {_srt_ts(seg.end)}")
        lines.append(seg.text.strip())
        lines.append("")
    return "\n".join(lines)


def _srt_ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        ms = 0
        s += 1
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_ass(segments: list[CaptionSegment], path: Path, options: CaptionOptions) -> Path:
    style = STYLE_PRESETS.get(options.style, STYLE_PRESETS[CaptionStyle.clean])
    fontsize = int(options.font_size * style["fontsize_mul"])
    alignment = {"bottom": 2, "center": 5, "top": 8}.get(options.position, 2)
    primary = _ass_color(options.color)
    outline_c = _ass_color(options.stroke)
    back = _ass_color(options.background)
    bold = style["bold"]
    outline = style["outline"]
    shadow = style["shadow"]
    border_style = 3 if options.background and options.background.lower() not in {"#00000000", "transparent"} else 1

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{options.font},{fontsize},{primary},&H000000FF,{outline_c},{back},{bold},0,0,0,100,100,0,0,{border_style},{outline},{shadow},{alignment},80,80,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events: list[str] = []
    for seg in segments:
        text = seg.text.replace("\n", r"\N").strip()
        if not text:
            continue
        events.append(f"Dialogue: 0,{_ts(seg.start)},{_ts(seg.end)},Default,,0,0,0,,{text}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return path


def remap_segments_through_keeps(
    captions: list[CaptionSegment],
    keep: list[tuple[float, float]],
) -> list[CaptionSegment]:
    """Map caption times from the original timeline onto a silence-trimmed timeline."""

    def map_time(t: float) -> float | None:
        offset = 0.0
        for start, end in keep:
            if t < start:
                return None
            if t <= end + 1e-3:
                return offset + (t - start)
            offset += max(0.0, end - start)
        return None

    remapped: list[CaptionSegment] = []
    for seg in captions:
        ns = map_time(seg.start)
        ne = map_time(seg.end)
        if ns is None and ne is None:
            continue
        if ns is None:
            ns = 0.0
        if ne is None:
            # clamp to end of keep timeline
            ne = sum(max(0.0, e - s) for s, e in keep)
        if ne <= ns:
            continue
        words = None
        if seg.words:
            mapped_words = []
            for w in seg.words:
                ws = map_time(w.start)
                we = map_time(w.end)
                if ws is None or we is None or we <= ws:
                    continue
                mapped_words.append(WordTiming(word=w.word, start=ws, end=we))
            words = mapped_words or None
        remapped.append(CaptionSegment(start=ns, end=ne, text=seg.text, words=words))
    return remapped


def ass_filter(ass_path: Path) -> str:
    # Prefer a relative-safe POSIX path; escape drive colon for filtergraphs
    ass_escaped = ass_path.resolve().as_posix().replace(":", "\\:")
    return f"ass='{ass_escaped}'"



def burn_captions(video_path: Path, ass_path: Path, output_path: Path, quality: str = "high") -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            "-i",
            str(video_path),
            "-vf",
            ass_filter(ass_path),
            *video_encode_args(quality),
            *audio_encode_args(),
            str(output_path),
        ]
    )
    return output_path


def auto_line_break(text: str, max_chars: int = 42) -> str:
    words = text.split()
    if not words:
        return text
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = (" ".join(current + [word])).strip()
        if len(trial) > max_chars and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines[:2])
