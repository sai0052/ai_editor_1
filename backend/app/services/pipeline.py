from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

from app.ai.filler import HeuristicFillerDetector
from app.ai.transcription import get_transcription_provider, transcript_to_caption_segments
from app.audio.denoise import denoise_video_audio
from app.audio.extract import extract_audio
from app.audio.silence import (
    PRESET_PARAMS,
    SilenceInterval,
    build_keep_segments,
    detect_silences,
    detect_silences_from_transcript_gaps,
    merge_silence_lists,
)
from app.models.schemas import EditOptions, EditSummary, JobStatus, SilencePreset, StageProgress
from app.services.job_manager import job_manager
from app.services.storage import StorageService
from app.utils.errors import AppError, MissingAudioError
from app.video.captions import ass_filter, remap_segments_through_keeps, segments_to_srt, write_ass
from app.video.color import build_color_filter
from app.video.compose import concat_segments_fast, render_once
from app.video.crop import reframe_filter
from app.video.encode import export_needs_reencode, export_video
from app.video.metadata import extract_metadata

logger = logging.getLogger(__name__)


def build_stages(options: EditOptions) -> list[StageProgress]:
    stages = [StageProgress(id="analyze", label="Analyzing video")]
    if options.noise.enabled:
        stages.append(StageProgress(id="noise", label="Removing background noise"))
    if options.silence.enabled or options.pauses.enabled:
        stages.append(StageProgress(id="silence", label="Removing long silences"))
    need_transcript = (
        options.captions.enabled
        or options.filler.enabled
        or options.silence.enabled
        or options.pauses.enabled
    )
    if need_transcript:
        stages.append(StageProgress(id="transcribe", label="Detecting speech"))
    if options.filler.enabled:
        stages.append(StageProgress(id="filler", label="Detecting filler words"))
    if options.jump_cuts.enabled:
        stages.append(StageProgress(id="jump_cuts", label="Creating jump cuts"))
    if options.captions.enabled:
        stages.append(StageProgress(id="captions", label="Generating captions"))
    if options.color.enabled:
        stages.append(StageProgress(id="color", label="Applying color grading"))
    if options.reframe.enabled:
        stages.append(StageProgress(id="reframe", label="Auto reframing"))
    stages.append(StageProgress(id="render", label="Rendering final video"))
    return stages


class EditPipeline:
    """
    Fast pipeline:
    - Audio-only ops copy the video stream (no re-encode)
    - Silence detection decodes audio only
    - Silence cuts use one filter_complex pass (not N encodes)
    - Color + captions + reframe + export collapse into a single encode when possible
    """

    def __init__(self, storage: StorageService | None = None):
        self.storage = storage or StorageService()

    async def run(self, job_id: str) -> None:
        job = job_manager.get(job_id)
        started = time.time()
        work = Path(job.work_dir)
        tmp = work / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        current = Path(job.original_path)
        summary = EditSummary()
        quality = job.export.quality.value

        try:
            await job_manager.update(job_id, status=JobStatus.analyzing)
            await self._stage(job_id, "analyze", "running")
            meta = extract_metadata(current, job.metadata.filename)
            duration = meta.duration or job.metadata.duration
            await self._stage(job_id, "analyze", "completed", detail=f"{meta.width}x{meta.height} · {duration:.1f}s")
            await self._refresh_eta(job_id, started)

            opts = job.options
            if (opts.noise.enabled or opts.silence.enabled or opts.captions.enabled or opts.filler.enabled) and not meta.has_audio:
                raise MissingAudioError("This video has no audio track, so audio-based edits cannot run.")

            # Deferred video filters — applied in one final encode
            pending_vf: list[str] = []
            ass_path: Path | None = None
            cut_segments: list[tuple[float, float]] | None = None
            needs_cut = False

            # --- Noise (video stream copy) ---
            if opts.noise.enabled:
                await job_manager.update(job_id, status=JobStatus.processing)
                await self._stage(job_id, "noise", "running")
                out = tmp / "noise.mp4"
                await _to_thread(denoise_video_audio, current, out, opts.noise.strength, quality)
                current = out
                summary.noise_reduced = True
                await self._stage(job_id, "noise", "completed", detail=f"Strength: {opts.noise.strength.value}")
                await self._refresh_eta(job_id, started)

            # --- Silence / pauses: detect now (adaptive), refine with transcript later ---
            silence_min = 0.55
            silence_keep = 0.15
            detected_silences: list[SilenceInterval] = []
            if opts.silence.enabled or opts.pauses.enabled:
                await self._stage(job_id, "silence", "running")
                silence_opts = opts.silence
                min_ms = silence_opts.min_silence_ms
                keep_ms = silence_opts.keep_silence_ms
                if opts.pauses.enabled and not opts.silence.enabled:
                    min_ms = min_ms or 350
                    keep_ms = keep_ms or 80
                elif opts.pauses.enabled and opts.silence.enabled:
                    keep_ms = keep_ms if keep_ms is not None else 120

                params = PRESET_PARAMS[silence_opts.preset]
                silence_min = (min_ms / 1000.0) if min_ms is not None else params["min_silence"]
                silence_keep = (keep_ms / 1000.0) if keep_ms is not None else params["keep"]
                detected_silences = await _to_thread(
                    detect_silences,
                    current,
                    min_silence=silence_min,
                    noise_db=params["noise_db"],
                    adaptive=True,
                    rel_db=params["rel_db"],
                    duration=duration,
                )
                if detected_silences:
                    cut_segments = build_keep_segments(duration, detected_silences, silence_keep)
                    needs_cut = _segments_are_meaningful(cut_segments, duration)
                    summary.silences_removed = len(detected_silences) if needs_cut else 0
                    if opts.pauses.enabled and needs_cut:
                        summary.pauses_shortened = len(detected_silences)
                    removed_sec = max(0.0, duration - sum(e - s for s, e in (cut_segments or [])))
                    detail = (
                        f"{len(detected_silences)} quiet sections · ~{removed_sec:.1f}s to remove"
                        if needs_cut
                        else "Quiet sections found but too short to cut"
                    )
                else:
                    detail = "No long silences found yet — will recheck after speech analysis"
                await self._stage(job_id, "silence", "completed", detail=detail)
                await self._refresh_eta(job_id, started)

            transcript = None
            need_transcript = (
                opts.captions.enabled
                or opts.filler.enabled
                or opts.silence.enabled  # speech-gap silence cuts are much more reliable
                or opts.pauses.enabled
            )
            if need_transcript:
                await self._stage(job_id, "transcribe", "running")
                try:
                    wav = tmp / "speech.wav"
                    await _to_thread(extract_audio, current, wav)
                    provider = get_transcription_provider()
                    transcript = await _to_thread(
                        provider.transcribe,
                        str(wav),
                        None if opts.captions.language == "auto" else opts.captions.language,
                    )
                    (tmp / "transcript.txt").write_text(transcript.full_text, encoding="utf-8")
                    await self._stage(
                        job_id,
                        "transcribe",
                        "completed",
                        detail=f"Language: {transcript.language} · {len(transcript.segments)} segments",
                    )
                except AppError as exc:
                    # Captions/filler require transcript; silence can fall back to energy detection
                    if opts.captions.enabled or opts.filler.enabled:
                        raise
                    transcript = None
                    await self._stage(
                        job_id,
                        "transcribe",
                        "completed",
                        detail=f"Speech analysis skipped ({exc.message}) — using audio energy only",
                    )
                await self._refresh_eta(job_id, started)

                # Refine silence cuts using speech gaps (handles room-tone "false loud" pauses)
                if transcript and (opts.silence.enabled or opts.pauses.enabled):
                    speech_spans = [(s.start, s.end) for s in transcript.segments if s.end > s.start]
                    gap_silences = detect_silences_from_transcript_gaps(
                        speech_spans,
                        duration=duration,
                        min_silence=silence_min,
                    )
                    # Prefer transcript gaps when available — room tone fools pure energy gates
                    if gap_silences:
                        combined = gap_silences
                        # Also include energy silences that sit inside those gaps (extra room-tone)
                        extra = [
                            s
                            for s in detected_silences
                            if any(s.start >= g.start - 0.05 and s.end <= g.end + 0.05 for g in gap_silences)
                        ]
                        combined = merge_silence_lists(combined, extra)
                    else:
                        combined = detected_silences
                    if combined:
                        cut_segments = build_keep_segments(duration, combined, silence_keep)
                        needs_cut = _segments_are_meaningful(cut_segments, duration)
                        summary.silences_removed = len(combined) if needs_cut else 0
                        if opts.pauses.enabled and needs_cut:
                            summary.pauses_shortened = len(combined)
                        removed_sec = max(0.0, duration - sum(e - s for s, e in (cut_segments or [(0, duration)])))
                        logger.info(
                            "Silence refine: energy=%d transcript_gaps=%d combined=%d needs_cut=%s remove~%.1fs",
                            len(detected_silences),
                            len(gap_silences),
                            len(combined),
                            needs_cut,
                            removed_sec,
                        )

            if opts.filler.enabled:
                await self._stage(job_id, "filler", "running")
                detector = HeuristicFillerDetector()
                hits = detector.detect(transcript) if transcript else []
                safe = [h for h in hits if h.safe_to_remove]
                review = [h for h in hits if not h.safe_to_remove]
                if opts.filler.mode.value == "remove" and safe:
                    intervals = [
                        SilenceInterval(max(0, h.start - 0.02), h.end + 0.02) for h in safe
                    ]
                    # Merge filler cuts into existing keep plan
                    base_segments = cut_segments or [(0.0, duration)]
                    # Convert filler intervals relative to current timeline into cuts on full timeline
                    filler_keep = build_keep_segments(duration, intervals, keep_silence=0.0)
                    cut_segments = _intersect_segments(base_segments, filler_keep) if cut_segments else filler_keep
                    needs_cut = True
                    summary.filler_removed = len(safe)
                    detail = f"Removed {len(safe)} fillers"
                    if review:
                        detail += f" · {len(review)} flagged for review (kept)"
                elif opts.filler.mode.value == "review":
                    summary.notes.append(f"{len(hits)} filler candidates marked for review (not removed).")
                    detail = f"{len(hits)} candidates (review mode)"
                else:
                    detail = "Fillers kept"
                await self._stage(job_id, "filler", "completed", detail=detail)
                await self._refresh_eta(job_id, started)

            if opts.jump_cuts.enabled:
                await self._stage(job_id, "jump_cuts", "running")
                if not opts.silence.enabled:
                    params = PRESET_PARAMS[SilencePreset.aggressive]
                    silences = await _to_thread(
                        detect_silences,
                        current,
                        min_silence=params["min_silence"],
                        noise_db=params["noise_db"],
                    )
                    if silences:
                        jump_keep = build_keep_segments(duration, silences, params["keep"])
                        cut_segments = _intersect_segments(cut_segments, jump_keep) if cut_segments else jump_keep
                        needs_cut = True
                        summary.jump_cuts = len(silences)
                        detail = f"{len(silences)} jump cuts queued"
                    else:
                        detail = "No jump cuts needed"
                else:
                    summary.jump_cuts = summary.silences_removed
                    detail = "Applied with silence cleanup"
                await self._stage(job_id, "jump_cuts", "completed", detail=detail)
                await self._refresh_eta(job_id, started)

            if opts.captions.enabled:
                await self._stage(job_id, "captions", "running")
                if not transcript:
                    raise AppError("Captions require speech transcription.", code="no_transcript")
                caps = transcript_to_caption_segments(transcript)
                if needs_cut and cut_segments:
                    caps = remap_segments_through_keeps(caps, cut_segments)
                srt_path = work / "captions.srt"
                ass_path = tmp / "captions.ass"
                srt_path.write_text(segments_to_srt(caps), encoding="utf-8")
                write_ass(caps, ass_path, opts.captions)
                if opts.captions.burn_in:
                    pending_vf.append(ass_filter(ass_path))
                summary.captions_generated = True
                await self._stage(job_id, "captions", "completed", detail=f"{len(caps)} cues · burn-in queued")
                await self._refresh_eta(job_id, started)

            if opts.color.enabled:
                await self._stage(job_id, "color", "running")
                color_opts = opts.color.model_copy()
                pending_vf.append(build_color_filter(color_opts))
                summary.color_applied = True
                await self._stage(job_id, "color", "completed", detail=f"{color_opts.preset.value} · queued")
                await self._refresh_eta(job_id, started)

            if opts.reframe.enabled:
                await self._stage(job_id, "reframe", "running")
                pending_vf.append(reframe_filter(opts.reframe.aspect.value))
                summary.reframed = True
                await self._stage(job_id, "reframe", "completed", detail=f"{opts.reframe.aspect.value} · queued")
                await self._refresh_eta(job_id, started)

            # --- Single render pass ---
            await job_manager.update(job_id, status=JobStatus.rendering)
            await self._stage(job_id, "render", "running")
            final_path = work / "output.mp4"
            vf = ",".join(pending_vf) if pending_vf else None

            # If export needs scale, fold into same pass
            export_vf = None
            if export_needs_reencode(job.export, meta.height):
                from app.models.schemas import ExportResolution
                from app.video.encode import RESOLUTION_MAP

                if job.export.resolution != ExportResolution.original:
                    target_h = RESOLUTION_MAP[job.export.resolution]
                    if not (meta.height and meta.height <= target_h):
                        export_vf = f"scale=-2:{target_h}"
                if export_vf:
                    vf = f"{vf},{export_vf}" if vf else export_vf

            rendered = tmp / "rendered.mp4"
            if needs_cut and cut_segments:
                await _to_thread(
                    concat_segments_fast,
                    current,
                    rendered,
                    cut_segments,
                    quality=quality,
                    video_filter=vf,
                )
                current = rendered
            elif vf:
                await _to_thread(render_once, current, rendered, quality=quality, video_filter=vf)
                current = rendered

            # Final export: stream-copy when possible (no second encode)
            meta_now = extract_metadata(current)
            if export_needs_reencode(job.export, meta_now.height) and not export_vf:
                await _to_thread(export_video, current, final_path, job.export, meta_now.height)
            else:
                if current.resolve() != final_path.resolve():
                    shutil.copy2(current, final_path)

            await self._stage(job_id, "render", "completed", detail="Ready (fast path)")
            await job_manager.update(
                job_id,
                status=JobStatus.completed,
                progress=100.0,
                summary=summary,
                result_path=str(final_path),
                eta_seconds=0,
            )
            self.storage.cleanup_job_temp(work)
        except AppError as exc:
            logger.warning("Job %s failed: %s", job_id, exc.message)
            await self._fail_running_stage(job_id, exc.message)
            await job_manager.update(job_id, status=JobStatus.failed, error=exc.message)
        except Exception:
            logger.exception("Job %s unexpected failure", job_id)
            msg = "Processing failed unexpectedly. Please try again with a different file or fewer options."
            await self._fail_running_stage(job_id, msg)
            await job_manager.update(job_id, status=JobStatus.failed, error=msg)

    async def _stage(self, job_id: str, stage_id: str, status: str, detail: str | None = None) -> None:
        await job_manager.set_stage(job_id, stage_id, status, detail=detail, progress=100.0 if status == "completed" else 10.0)

    async def _fail_running_stage(self, job_id: str, message: str) -> None:
        job = job_manager.get(job_id)
        for stage in job.stages:
            if stage.status == "running":
                await job_manager.set_stage(job_id, stage.id, "failed", detail=message)
                break

    async def _refresh_eta(self, job_id: str, started: float) -> None:
        job = job_manager.get(job_id)
        done = sum(1 for s in job.stages if s.status in ("completed", "skipped", "failed"))
        total = max(1, len(job.stages))
        elapsed = max(0.1, time.time() - started)
        if done <= 0:
            eta = None
        else:
            per = elapsed / done
            eta = max(0.0, per * (total - done))
        await job_manager.update(job_id, eta_seconds=eta)


def _intersect_segments(
    a: list[tuple[float, float]] | None,
    b: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Intersect two keep-segment lists (AND of timelines)."""
    if not a:
        return b
    out: list[tuple[float, float]] = []
    for as_, ae in a:
        for bs, be in b:
            s = max(as_, bs)
            e = min(ae, be)
            if e - s > 0.05:
                out.append((s, e))
    return out or a


def _segments_are_meaningful(segments: list[tuple[float, float]] | None, duration: float) -> bool:
    if not segments:
        return False
    if len(segments) == 1 and abs(segments[0][0]) < 0.02 and abs(segments[0][1] - duration) < 0.08:
        return False
    kept = sum(e - s for s, e in segments)
    return kept < duration - 0.08


async def _to_thread(fn, *args, **kwargs):
    import asyncio
    from functools import partial

    return await asyncio.to_thread(partial(fn, *args, **kwargs))
