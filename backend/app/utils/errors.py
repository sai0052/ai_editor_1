from __future__ import annotations


class AppError(Exception):
    """User-facing application error."""

    def __init__(self, message: str, code: str = "app_error", status_code: int = 400, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class InvalidVideoError(AppError):
    def __init__(self, message: str = "The uploaded file is not a valid video.", details: dict | None = None):
        super().__init__(message, code="invalid_video", status_code=400, details=details)


class UnsupportedFormatError(AppError):
    def __init__(self, message: str = "This video format is not supported.", details: dict | None = None):
        super().__init__(message, code="unsupported_format", status_code=400, details=details)


class FileTooLargeError(AppError):
    def __init__(self, message: str = "This file exceeds the maximum upload size.", details: dict | None = None):
        super().__init__(message, code="file_too_large", status_code=413, details=details)


class MissingAudioError(AppError):
    def __init__(self, message: str = "This video has no audio track.", details: dict | None = None):
        super().__init__(message, code="missing_audio", status_code=400, details=details)


class NoSpeechError(AppError):
    def __init__(self, message: str = "No speech was detected in this video.", details: dict | None = None):
        super().__init__(message, code="no_speech", status_code=422, details=details)


class FFmpegError(AppError):
    def __init__(self, message: str = "Video processing failed. Please try again.", details: dict | None = None):
        super().__init__(message, code="ffmpeg_error", status_code=500, details=details)


class AIProviderError(AppError):
    def __init__(self, message: str = "AI processing is temporarily unavailable.", details: dict | None = None):
        super().__init__(message, code="ai_error", status_code=503, details=details)


class JobNotFoundError(AppError):
    def __init__(self, message: str = "Job not found.", details: dict | None = None):
        super().__init__(message, code="job_not_found", status_code=404, details=details)


class VideoNotFoundError(AppError):
    def __init__(self, message: str = "Video not found.", details: dict | None = None):
        super().__init__(message, code="video_not_found", status_code=404, details=details)


class ProcessingTimeoutError(AppError):
    def __init__(self, message: str = "Processing timed out. Try a shorter clip or fewer operations.", details: dict | None = None):
        super().__init__(message, code="timeout", status_code=504, details=details)
