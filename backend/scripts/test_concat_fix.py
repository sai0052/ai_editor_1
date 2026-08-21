from pathlib import Path

from app.models.schemas import CaptionOptions, ColorOptions, ColorPreset
from app.video.captions import CaptionSegment, ass_filter, remap_segments_through_keeps, write_ass
from app.video.color import build_color_filter
from app.video.compose import concat_segments_fast

src = Path("storage/temp/sample.mp4")
out = Path("storage/temp/fix_concat.mp4")
segs = [(0.0, 0.8), (1.2, 2.0)]
vf = build_color_filter(ColorOptions(enabled=True, preset=ColorPreset.natural))
caps = [CaptionSegment(0.1, 0.6, "hello"), CaptionSegment(1.3, 1.8, "world")]
mapped = remap_segments_through_keeps(caps, segs)
print("mapped", [(round(c.start, 2), round(c.end, 2), c.text) for c in mapped])
ass = Path("storage/temp/t.ass")
write_ass(mapped, ass, CaptionOptions())
combo = f"{ass_filter(ass)},{vf}"
concat_segments_fast(src, out, segs, quality="standard", video_filter=combo)
print("ok", out.exists(), out.stat().st_size)
