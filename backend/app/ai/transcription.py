from __future__ import annotations

import logging
from pathlib import Path

from app.ai.base import Transcript, TranscriptSegment, TranscriptionProvider, WordSpan
from app.config import get_settings
from app.utils.errors import AIProviderError, NoSpeechError
from app.video.captions import CaptionSegment, auto_line_break

logger = logging.getLogger(__name__)


class FasterWhisperProvider(TranscriptionProvider):
    name = "faster-whisper"

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:
            raise AIProviderError(
                "Local captions require faster-whisper. Install with: pip install faster-whisper"
            ) from exc
        self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, audio_path: str, language: str | None = None) -> Transcript:
        model = self._load()
        lang = None if not language or language == "auto" else language
        segments_iter, info = model.transcribe(
            audio_path,
            language=lang,
            word_timestamps=True,
            vad_filter=True,
        )
        segments: list[TranscriptSegment] = []
        texts: list[str] = []
        for seg in segments_iter:
            words = [
                WordSpan(word=w.word.strip(), start=float(w.start), end=float(w.end))
                for w in (seg.words or [])
                if w.word and w.word.strip()
            ]
            text = (seg.text or "").strip()
            if not text:
                continue
            segments.append(
                TranscriptSegment(start=float(seg.start), end=float(seg.end), text=text, words=words)
            )
            texts.append(text)
        if not segments:
            raise NoSpeechError()
        return Transcript(
            language=getattr(info, "language", language or "unknown") or "unknown",
            segments=segments,
            full_text=" ".join(texts),
        )


def _parse_verbose_transcript(payload: dict) -> Transcript:
    segments: list[TranscriptSegment] = []
    for seg in payload.get("segments") or []:
        words = [
            WordSpan(word=w.get("word", "").strip(), start=float(w.get("start", 0)), end=float(w.get("end", 0)))
            for w in (seg.get("words") or [])
            if w.get("word")
        ]
        text = (seg.get("text") or "").strip()
        if text:
            segments.append(
                TranscriptSegment(
                    start=float(seg.get("start", 0)),
                    end=float(seg.get("end", 0)),
                    text=text,
                    words=words,
                )
            )
    if not segments and payload.get("text"):
        segments.append(TranscriptSegment(start=0, end=0, text=payload["text"].strip(), words=[]))
    if not segments:
        raise NoSpeechError()
    return Transcript(
        language=payload.get("language") or "unknown",
        segments=segments,
        full_text=payload.get("text", ""),
    )


class OpenAIWhisperProvider(TranscriptionProvider):
    name = "openai"

    def transcribe(self, audio_path: str, language: str | None = None) -> Transcript:
        settings = get_settings()
        if not settings.openai_api_key:
            raise AIProviderError("OpenAI API key is not configured.")
        return _http_transcribe(
            audio_path=audio_path,
            language=language,
            api_key=settings.openai_api_key,
            url="https://api.openai.com/v1/audio/transcriptions",
            model="whisper-1",
            provider_label="OpenAI",
        )


class GroqWhisperProvider(TranscriptionProvider):
    name = "groq"

    def transcribe(self, audio_path: str, language: str | None = None) -> Transcript:
        settings = get_settings()
        if not settings.groq_api_key:
            raise AIProviderError("Groq API key is not configured.")
        return _http_transcribe(
            audio_path=audio_path,
            language=language,
            api_key=settings.groq_api_key,
            url="https://api.groq.com/openai/v1/audio/transcriptions",
            model=settings.groq_whisper_model,
            provider_label="Groq",
        )


def _http_transcribe(
    *,
    audio_path: str,
    language: str | None,
    api_key: str,
    url: str,
    model: str,
    provider_label: str,
) -> Transcript:
    try:
        import httpx
    except ImportError as exc:
        raise AIProviderError("httpx is required for cloud transcription.") from exc

    headers = {"Authorization": f"Bearer {api_key}"}
    data: dict[str, str] = {"model": model, "response_format": "verbose_json"}
    if language and language != "auto":
        data["language"] = language

    with httpx.Client(timeout=300.0) as client:
        with open(audio_path, "rb") as f:
            files = {"file": (Path(audio_path).name, f, "audio/wav")}
            resp = client.post(url, headers=headers, data=data, files=files)

    if resp.status_code >= 400:
        detail = (resp.text or "")[:300]
        logger.error("%s transcription HTTP %s: %s", provider_label, resp.status_code, detail)
        raise AIProviderError(
            f"{provider_label} transcription failed. Check your API key and account access.",
            details={"status": resp.status_code},
        )
    return _parse_verbose_transcript(resp.json())


def get_transcription_provider() -> TranscriptionProvider:
    settings = get_settings()
    choice = (settings.transcription_provider or "auto").lower()
    if choice == "groq":
        return GroqWhisperProvider()
    if choice == "openai":
        return OpenAIWhisperProvider()
    if choice == "faster-whisper":
        return FasterWhisperProvider(settings.whisper_model)
    if choice == "none":
        raise AIProviderError("Transcription provider is disabled.")
    # auto: groq → faster-whisper → openai
    if settings.groq_api_key:
        return GroqWhisperProvider()
    try:
        import faster_whisper  # noqa: F401

        return FasterWhisperProvider(settings.whisper_model)
    except ImportError:
        if settings.openai_api_key:
            return OpenAIWhisperProvider()
        raise AIProviderError(
            "No transcription provider available. Set GROQ_API_KEY, OPENAI_API_KEY, or install faster-whisper."
        )


def transcript_to_caption_segments(transcript: Transcript) -> list[CaptionSegment]:
    result: list[CaptionSegment] = []
    for seg in transcript.segments:
        text = auto_line_break(seg.text)
        words = None
        if seg.words:
            from app.video.captions import WordTiming

            words = [WordTiming(word=w.word, start=w.start, end=w.end) for w in seg.words]
        result.append(CaptionSegment(start=seg.start, end=seg.end, text=text, words=words))
    return result
