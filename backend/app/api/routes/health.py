from fastapi import APIRouter

from app.config import get_settings
from app.video.ffmpeg import _bin

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    settings = get_settings()
    ffmpeg_ok = False
    ffprobe_ok = False
    try:
        _bin("ffmpeg")
        ffmpeg_ok = True
    except Exception:
        pass
    try:
        _bin("ffprobe")
        ffprobe_ok = True
    except Exception:
        pass
    return {
        "status": "ok" if ffmpeg_ok and ffprobe_ok else "degraded",
        "app": settings.app_name,
        "ffmpeg": ffmpeg_ok,
        "ffprobe": ffprobe_ok,
    }
